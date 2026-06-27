from datetime import date
from flask import Blueprint, request, jsonify, g
from ..supabase_client import supabase, get_user_client
from ..auth.middleware import require_auth, require_role

mensalidades_bp = Blueprint("mensalidades", __name__, url_prefix="/mensalidades")


@mensalidades_bp.get("")
@require_role("admin", "recepcionista")
def listar():
    status = request.args.get("status")       # pendente | paga | atrasada
    aluno_id = request.args.get("aluno_id")
    mes = request.args.get("mes")             # formato: 2026-06

    query = (
        supabase.table("mensalidades")
        .select("*, aluno_planos(aluno_id, planos(nome), alunos(profiles(nome)))")
    )

    if status:
        query = query.eq("status", status)
    if mes:
        query = query.gte("data_vencimento", f"{mes}-01").lte(
            "data_vencimento", f"{mes}-31"
        )
    if aluno_id:
        query = query.eq("aluno_planos.aluno_id", aluno_id)

    result = query.order("data_vencimento", desc=True).execute()
    return jsonify(result.data)


@mensalidades_bp.get("/<uuid:mensalidade_id>")
@require_auth
def buscar(mensalidade_id):
    # RLS por identidade: admin/recepcionista veem todas; aluno só as suas.
    # Antes a service_role devolvia qualquer mensalidade a qualquer autenticado.
    db = get_user_client(g.access_token)
    result = (
        db.table("mensalidades")
        .select("*, aluno_planos(aluno_id, planos(nome, valor))")
        .eq("id", str(mensalidade_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Mensalidade não encontrada"}), 404
    return jsonify(result.data)


@mensalidades_bp.post("/<uuid:mensalidade_id>/pagar")
@require_role("admin", "recepcionista")
def registrar_pagamento(mensalidade_id):
    mensalidade = (
        supabase.table("mensalidades")
        .select("*")
        .eq("id", str(mensalidade_id))
        .single()
        .execute()
    )
    if not mensalidade.data:
        return jsonify({"error": "Mensalidade não encontrada"}), 404

    m = mensalidade.data

    if m["status"] == "paga":
        return jsonify({"error": "Mensalidade já foi paga"}), 400

    # Calcula juros se estiver atrasada (2% ao mês proporcional por dia)
    juros = 0.0
    hoje = date.today()
    vcto = date.fromisoformat(m["data_vencimento"])

    if hoje > vcto:
        dias_atraso = (hoje - vcto).days
        juros = round(m["valor"] * 0.02 * (dias_atraso / 30), 2)

    result = (
        supabase.table("mensalidades")
        .update({
            "status": "paga",
            "data_pagamento": hoje.isoformat(),
            "juros": juros,
        })
        .eq("id", str(mensalidade_id))
        .execute()
    )

    # Verifica se aluno ainda tem mensalidades atrasadas após o pagamento
    aluno_plano_id = m["aluno_plano_id"]
    aluno_plano = (
        supabase.table("aluno_planos")
        .select("aluno_id")
        .eq("id", aluno_plano_id)
        .single()
        .execute()
    )
    if aluno_plano.data:
        aluno_id = aluno_plano.data["aluno_id"]
        pendentes = (
            supabase.table("mensalidades")
            .select("id, aluno_plano_id, aluno_planos!inner(aluno_id)")
            .eq("aluno_planos.aluno_id", aluno_id)
            .eq("status", "atrasada")
            .execute()
        )
        if not pendentes.data:
            supabase.table("alunos").update({"status": "ativo"}).eq(
                "id", aluno_id
            ).execute()

    return jsonify(result.data[0])

from flask import Blueprint, jsonify, g
from ..supabase_client import supabase
from ..auth.middleware import require_auth

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


def _aluno_do_usuario():
    """Retorna o registro do aluno pelo profile_id do usuário logado."""
    result = (
        supabase.table("alunos")
        .select("id, status, frequencia_habilitada")
        .eq("profile_id", g.user_id)
        .single()
        .execute()
    )
    return result.data


@portal_bp.get("/me")
@require_auth
def me():
    aluno = _aluno_do_usuario()
    if not aluno:
        return jsonify({"error": "Aluno não encontrado para este usuário"}), 404

    profile = (
        supabase.table("profiles")
        .select("nome, telefone")
        .eq("id", g.user_id)
        .single()
        .execute()
        .data
    )

    planos_ativos = (
        supabase.table("aluno_planos")
        .select("planos(nome)")
        .eq("aluno_id", aluno["id"])
        .eq("status", "ativo")
        .execute()
        .data
    )

    return jsonify({
        "nome": profile.get("nome", "—"),
        "telefone": profile.get("telefone"),
        "status": aluno["status"],
        "frequencia_habilitada": aluno["frequencia_habilitada"],
        "planos": [
            ap["planos"]["nome"]
            for ap in planos_ativos
            if ap.get("planos")
        ],
    })


@portal_bp.get("/mensalidades")
@require_auth
def mensalidades():
    aluno = _aluno_do_usuario()
    if not aluno:
        return jsonify([])

    ap_ids = [
        ap["id"]
        for ap in supabase.table("aluno_planos")
        .select("id")
        .eq("aluno_id", aluno["id"])
        .execute()
        .data
    ]

    if not ap_ids:
        return jsonify([])

    result = (
        supabase.table("mensalidades")
        .select("id, valor, juros, valor_total, data_vencimento, data_pagamento, status, "
                "aluno_planos(planos(nome))")
        .in_("aluno_plano_id", ap_ids)
        .order("data_vencimento", desc=True)
        .execute()
    )
    return jsonify(result.data)


@portal_bp.get("/frequencias")
@require_auth
def frequencias():
    aluno = _aluno_do_usuario()
    if not aluno or not aluno["frequencia_habilitada"]:
        return jsonify([])

    result = (
        supabase.table("frequencias")
        .select("id, data_hora")
        .eq("aluno_id", aluno["id"])
        .order("data_hora", desc=True)
        .limit(60)
        .execute()
    )
    return jsonify(result.data)

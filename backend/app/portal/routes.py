from datetime import date, timedelta
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
        .maybe_single()
        .execute()
    )
    return result.data if result else None


@portal_bp.get("/me")
@require_auth
def me():
    aluno = _aluno_do_usuario()
    if not aluno:
        return jsonify({"error": "Aluno não encontrado para este usuário"}), 404

    profile_result = (
        supabase.table("profiles")
        .select("nome, telefone")
        .eq("id", g.user_id)
        .maybe_single()
        .execute()
    )
    profile = profile_result.data if profile_result else {}

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


@portal_bp.get("/avaliacoes")
@require_auth
def portal_avaliacoes():
    aluno = _aluno_do_usuario()
    if not aluno:
        return jsonify({"avaliacoes": [], "proxima_avaliacao": None})

    result = (
        supabase.table("avaliacoes")
        .select(
            "id, data_avaliacao, peso_kg, altura_cm, imc, gordura_corporal, "
            "massa_magra_kg, circ_cintura, circ_quadril, circ_braco, circ_coxa, circ_peito"
        )
        .eq("aluno_id", aluno["id"])
        .order("data_avaliacao", desc=True)
        .limit(5)
        .execute()
    )

    dados = result.data or []
    proxima = None
    if dados:
        try:
            ultima = date.fromisoformat(dados[0]["data_avaliacao"])
            proxima = (ultima + timedelta(days=90)).isoformat()
        except (ValueError, KeyError):
            pass

    return jsonify({"avaliacoes": dados, "proxima_avaliacao": proxima})


@portal_bp.get("/treino")
@require_auth
def portal_treino():
    aluno = _aluno_do_usuario()
    if not aluno:
        return jsonify([])

    result = (
        supabase.table("fichas_treino")
        .select(
            "id, nome, divisao, observacoes, "
            "exercicios_ficha(id, nome, series, repeticoes, carga_kg, descanso_seg, ordem, observacoes)"
        )
        .eq("aluno_id", aluno["id"])
        .eq("ativa", True)
        .order("divisao")
        .execute()
    )

    fichas = result.data or []
    for ficha in fichas:
        exs = ficha.get("exercicios_ficha") or []
        ficha["exercicios_ficha"] = sorted(exs, key=lambda e: e.get("ordem", 0))

    return jsonify(fichas)


@portal_bp.get("/avisos")
@require_auth
def portal_avisos():
    hoje = date.today().isoformat()

    result = (
        supabase.table("avisos")
        .select("id, titulo, mensagem, tipo, data_inicio, data_fim")
        .eq("ativo", True)
        .lte("data_inicio", hoje)
        .or_(f"data_fim.is.null,data_fim.gte.{hoje}")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    return jsonify(result.data or [])

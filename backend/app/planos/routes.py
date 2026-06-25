from flask import Blueprint, request, jsonify, g
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role

planos_bp = Blueprint("planos", __name__, url_prefix="/planos")


@planos_bp.get("")
@require_auth
def listar():
    # Admin vê todos; demais veem só os ativos
    query = supabase.table("planos").select("*, instrutor_planos(instrutores(profiles(nome)))")

    if g.user_tipo != "admin":
        query = query.eq("ativo", True)

    result = query.order("nome").execute()
    return jsonify(result.data)


@planos_bp.post("")
@require_role("admin")
def criar():
    data = request.get_json(silent=True) or {}

    for campo in ("nome", "valor", "duracao_dias"):
        if data.get(campo) is None:
            return jsonify({"error": f"Campo '{campo}' é obrigatório"}), 400

    if float(data["valor"]) <= 0:
        return jsonify({"error": "Valor deve ser maior que zero"}), 400

    if int(data["duracao_dias"]) <= 0:
        return jsonify({"error": "Duração deve ser maior que zero"}), 400

    result = supabase.table("planos").insert({
        "nome": data["nome"],
        "descricao": data.get("descricao"),
        "valor": float(data["valor"]),
        "duracao_dias": int(data["duracao_dias"]),
    }).execute()

    return jsonify(result.data[0]), 201


@planos_bp.get("/<uuid:plano_id>")
@require_auth
def buscar(plano_id):
    result = (
        supabase.table("planos")
        .select("*, instrutor_planos(instrutores(profiles(nome)))")
        .eq("id", str(plano_id))
        .single()
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Plano não encontrado"}), 404
    return jsonify(result.data)


@planos_bp.put("/<uuid:plano_id>")
@require_role("admin")
def atualizar(plano_id):
    data = request.get_json(silent=True) or {}
    campos_permitidos = {"nome", "descricao", "valor", "duracao_dias"}
    update = {k: v for k, v in data.items() if k in campos_permitidos}

    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    result = (
        supabase.table("planos")
        .update(update)
        .eq("id", str(plano_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Plano não encontrado"}), 404
    return jsonify(result.data[0])


@planos_bp.patch("/<uuid:plano_id>/ativo")
@require_role("admin")
def toggle_ativo(plano_id):
    atual = (
        supabase.table("planos")
        .select("ativo")
        .eq("id", str(plano_id))
        .single()
        .execute()
    )
    if not atual.data:
        return jsonify({"error": "Plano não encontrado"}), 404

    novo = not atual.data["ativo"]
    result = (
        supabase.table("planos")
        .update({"ativo": novo})
        .eq("id", str(plano_id))
        .execute()
    )
    return jsonify(result.data[0])

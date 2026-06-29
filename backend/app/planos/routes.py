from flask import Blueprint, jsonify, g
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role
from ..schemas import PlanoCreateSchema, PlanoUpdateSchema
from ..validation import validate_body

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
@validate_body(PlanoCreateSchema)
def criar(payload: PlanoCreateSchema):
    result = supabase.table("planos").insert({
        "nome": payload.nome,
        "descricao": payload.descricao,
        "valor": payload.valor,
        "duracao_dias": payload.duracao_dias,
    }).execute()

    return jsonify(result.data[0]), 201


@planos_bp.get("/<uuid:plano_id>")
@require_auth
def buscar(plano_id):
    result = (
        supabase.table("planos")
        .select("*, instrutor_planos(instrutores(profiles(nome)))")
        .eq("id", str(plano_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Plano não encontrado"}), 404
    return jsonify(result.data)


@planos_bp.put("/<uuid:plano_id>")
@require_role("admin")
@validate_body(PlanoUpdateSchema)
def atualizar(plano_id, payload: PlanoUpdateSchema):
    update = payload.model_dump(exclude_unset=True)

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
        .maybe_single()
        .execute()
    )
    if not atual or not atual.data:
        return jsonify({"error": "Plano não encontrado"}), 404

    novo = not atual.data["ativo"]
    result = (
        supabase.table("planos")
        .update({"ativo": novo})
        .eq("id", str(plano_id))
        .execute()
    )
    return jsonify(result.data[0])

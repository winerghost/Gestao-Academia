from flask import Blueprint, request, jsonify, g
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role

instrutores_bp = Blueprint("instrutores", __name__, url_prefix="/instrutores")


# ── Instrutores ───────────────────────────────────────────────────────────────

@instrutores_bp.get("")
@require_role("admin", "recepcionista")
def listar():
    result = (
        supabase.table("instrutores")
        .select("*, profiles(nome, telefone)")
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(result.data)


@instrutores_bp.post("")
@require_role("admin")
def criar():
    data = request.get_json(silent=True) or {}

    for campo in ("nome", "email", "senha"):
        if not data.get(campo):
            return jsonify({"error": f"Campo '{campo}' é obrigatório"}), 400

    # 1. Cria usuário no Supabase Auth
    try:
        user_resp = supabase.auth.admin.create_user({
            "email": data["email"],
            "password": data["senha"],
            "email_confirm": True,
            "user_metadata": {"nome": data["nome"], "tipo": "instrutor"},
        })
        user_id = user_resp.user.id
    except Exception as e:
        return jsonify({"error": "Erro ao criar usuário", "detail": str(e)}), 400

    # 2. Cria registro do instrutor
    try:
        inst_resp = supabase.table("instrutores").insert({
            "profile_id": user_id,
            "especialidade": data.get("especialidade"),
            "modalidade": data.get("modalidade"),
            "salario": data.get("salario"),
            "data_admissao": data.get("data_admissao"),
        }).execute()
        return jsonify(inst_resp.data[0]), 201
    except Exception as e:
        supabase.auth.admin.delete_user(user_id)
        return jsonify({"error": "Erro ao salvar instrutor", "detail": str(e)}), 400


@instrutores_bp.get("/<uuid:instrutor_id>")
@require_auth
def buscar(instrutor_id):
    result = (
        supabase.table("instrutores")
        .select("*, profiles(nome, telefone)")
        .eq("id", str(instrutor_id))
        .single()
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Instrutor não encontrado"}), 404
    return jsonify(result.data)


@instrutores_bp.put("/<uuid:instrutor_id>")
@require_role("admin")
def atualizar(instrutor_id):
    data = request.get_json(silent=True) or {}
    campos_permitidos = {"especialidade", "modalidade", "salario", "data_admissao"}
    update = {k: v for k, v in data.items() if k in campos_permitidos}

    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    result = (
        supabase.table("instrutores")
        .update(update)
        .eq("id", str(instrutor_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Instrutor não encontrado"}), 404
    return jsonify(result.data[0])


# ── Vínculos instrutor ↔ plano ────────────────────────────────────────────────

@instrutores_bp.get("/<uuid:instrutor_id>/planos")
@require_role("admin", "recepcionista")
def listar_planos(instrutor_id):
    result = (
        supabase.table("instrutor_planos")
        .select("*, planos(nome, valor)")
        .eq("instrutor_id", str(instrutor_id))
        .execute()
    )
    return jsonify(result.data)


@instrutores_bp.post("/<uuid:instrutor_id>/planos")
@require_role("admin")
def vincular_plano(instrutor_id):
    data = request.get_json(silent=True) or {}

    if not data.get("plano_id"):
        return jsonify({"error": "Campo 'plano_id' é obrigatório"}), 400

    result = supabase.table("instrutor_planos").insert({
        "instrutor_id": str(instrutor_id),
        "plano_id": data["plano_id"],
    }).execute()

    return jsonify(result.data[0]), 201


@instrutores_bp.delete("/<uuid:instrutor_id>/planos/<uuid:instrutor_plano_id>")
@require_role("admin")
def desvincular_plano(instrutor_id, instrutor_plano_id):
    result = (
        supabase.table("instrutor_planos")
        .delete()
        .eq("id", str(instrutor_plano_id))
        .eq("instrutor_id", str(instrutor_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Vínculo não encontrado"}), 404
    return jsonify({"message": "Vínculo removido com sucesso"})

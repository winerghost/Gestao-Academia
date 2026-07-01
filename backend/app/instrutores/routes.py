from flask import Blueprint, jsonify, g, current_app
from ..supabase_client import supabase, get_user_client
from ..auth.middleware import require_auth, require_role
from ..schemas import (
    InstrutorCreateSchema,
    InstrutorUpdateSchema,
    VincularPlanoInstrutorSchema,
)
from ..validation import validate_body
from ..errors import email_ja_cadastrado, erro_campo

instrutores_bp = Blueprint("instrutores", __name__, url_prefix="/instrutores")


# ── Instrutores ───────────────────────────────────────────────────────────────

@instrutores_bp.get("")
@require_role("admin", "recepcionista")
def listar():
    # profiles!inner garante que só aparecem instrutores cujo tipo ainda é
    # "instrutor" — remove automaticamente quem foi rebaixado via Kanban.
    result = (
        supabase.table("instrutores")
        .select("*, profiles!inner(nome, telefone)")
        .filter("profiles.tipo", "eq", "instrutor")
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(result.data)


@instrutores_bp.post("")
@require_role("admin")
@validate_body(InstrutorCreateSchema)
def criar(payload: InstrutorCreateSchema):
    # 1. Cria usuário no Supabase Auth
    try:
        user_resp = supabase.auth.admin.create_user({
            "email": payload.email,
            "password": payload.senha,
            "email_confirm": True,
            "user_metadata": {"nome": payload.nome, "tipo": "instrutor"},
        })
        user_id = user_resp.user.id
    except Exception as e:
        current_app.logger.exception("Falha ao criar usuário no Supabase Auth")
        if email_ja_cadastrado(e):
            return erro_campo("email", "E-mail já cadastrado.", 400)
        return jsonify({"error": "Não foi possível criar o usuário"}), 400

    # 2. Cria registro do instrutor
    try:
        inst_resp = supabase.table("instrutores").insert({
            "profile_id": user_id,
            "especialidade": payload.especialidade,
            "modalidade": payload.modalidade,
            "salario": payload.salario,
            "data_admissao": payload.data_admissao.isoformat() if payload.data_admissao else None,
        }).execute()
        return jsonify(inst_resp.data[0]), 201
    except Exception:
        supabase.auth.admin.delete_user(user_id)
        current_app.logger.exception("Falha ao salvar instrutor; usuário do Auth revertido")
        return jsonify({"error": "Não foi possível salvar o instrutor"}), 400


@instrutores_bp.get("/<uuid:instrutor_id>")
@require_auth
def buscar(instrutor_id):
    # RLS por identidade: admin/recepcionista veem todos; instrutor só a si
    # mesmo; aluno não vê nenhum. Antes a service_role expunha salário e dados
    # de qualquer instrutor para qualquer autenticado (BOLA).
    db = get_user_client(g.access_token)
    result = (
        db.table("instrutores")
        .select("*, profiles(nome, telefone)")
        .eq("id", str(instrutor_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Instrutor não encontrado"}), 404
    return jsonify(result.data)


@instrutores_bp.put("/<uuid:instrutor_id>")
@require_role("admin")
@validate_body(InstrutorUpdateSchema)
def atualizar(instrutor_id, payload: InstrutorUpdateSchema):
    update = payload.model_dump(exclude_unset=True)
    if update.get("data_admissao") is not None:
        update["data_admissao"] = update["data_admissao"].isoformat()

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
@validate_body(VincularPlanoInstrutorSchema)
def vincular_plano(instrutor_id, payload: VincularPlanoInstrutorSchema):
    result = supabase.table("instrutor_planos").insert({
        "instrutor_id": str(instrutor_id),
        "plano_id": str(payload.plano_id),
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

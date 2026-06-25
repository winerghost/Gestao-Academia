import re
from datetime import date
from flask import Blueprint, request, jsonify, g
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role

alunos_bp = Blueprint("alunos", __name__, url_prefix="/alunos")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validar_cpf(cpf: str) -> str | None:
    """Remove formatação e valida que tem 11 dígitos. Retorna CPF limpo ou None."""
    cpf = re.sub(r"\D", "", cpf)
    return cpf if len(cpf) == 11 else None


# ── Alunos ────────────────────────────────────────────────────────────────────

@alunos_bp.get("")
@require_role("admin", "recepcionista")
def listar():
    status = request.args.get("status")   # ativo | inativo | inadimplente
    cpf = request.args.get("cpf")

    query = supabase.table("alunos").select("*, profiles(nome, telefone)")

    if status:
        query = query.eq("status", status)
    if cpf:
        cpf_limpo = re.sub(r"\D", "", cpf)
        query = query.eq("cpf", cpf_limpo)

    result = query.order("created_at", desc=True).execute()
    return jsonify(result.data)


@alunos_bp.post("")
@require_role("admin", "recepcionista")
def criar():
    data = request.get_json(silent=True) or {}

    for campo in ("nome", "email", "senha", "cpf"):
        if not data.get(campo):
            return jsonify({"error": f"Campo '{campo}' é obrigatório"}), 400

    cpf = _validar_cpf(data["cpf"])
    if not cpf:
        return jsonify({"error": "CPF inválido — informe 11 dígitos"}), 400

    # 1. Cria usuário no Supabase Auth (trigger cria o profile automaticamente)
    try:
        user_resp = supabase.auth.admin.create_user({
            "email": data["email"],
            "password": data["senha"],
            "email_confirm": True,
            "user_metadata": {"nome": data["nome"], "tipo": "aluno"},
        })
        user_id = user_resp.user.id
    except Exception as e:
        return jsonify({"error": "Erro ao criar usuário", "detail": str(e)}), 400

    # 2. Cria registro do aluno vinculado ao profile
    try:
        aluno_resp = supabase.table("alunos").insert({
            "profile_id": user_id,
            "cpf": cpf,
            "data_nascimento": data.get("data_nascimento"),
            "endereco": data.get("endereco"),
            "frequencia_habilitada": data.get("frequencia_habilitada", False),
        }).execute()
        return jsonify(aluno_resp.data[0]), 201
    except Exception as e:
        # Rollback: remove o usuário criado se o aluno falhar
        supabase.auth.admin.delete_user(user_id)
        return jsonify({"error": "Erro ao salvar aluno", "detail": str(e)}), 400


@alunos_bp.get("/<uuid:aluno_id>")
@require_auth
def buscar(aluno_id):
    # Instrutor só vê alunos dos seus planos (RLS garante no banco)
    result = (
        supabase.table("alunos")
        .select("*, profiles(nome, telefone), aluno_planos(id, status, data_inicio, data_fim, planos(nome, valor))")
        .eq("id", str(aluno_id))
        .single()
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Aluno não encontrado"}), 404
    return jsonify(result.data)


@alunos_bp.put("/<uuid:aluno_id>")
@require_role("admin", "recepcionista")
def atualizar(aluno_id):
    data = request.get_json(silent=True) or {}
    campos_permitidos = {"cpf", "data_nascimento", "endereco", "frequencia_habilitada"}
    update = {k: v for k, v in data.items() if k in campos_permitidos}

    if "cpf" in update:
        cpf = _validar_cpf(update["cpf"])
        if not cpf:
            return jsonify({"error": "CPF inválido"}), 400
        update["cpf"] = cpf

    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    result = (
        supabase.table("alunos")
        .update(update)
        .eq("id", str(aluno_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Aluno não encontrado"}), 404
    return jsonify(result.data[0])


@alunos_bp.patch("/<uuid:aluno_id>/status")
@require_role("admin", "recepcionista")
def atualizar_status(aluno_id):
    data = request.get_json(silent=True) or {}
    novo_status = data.get("status")

    if novo_status not in ("ativo", "inativo", "inadimplente"):
        return jsonify({"error": "Status inválido"}), 400

    result = (
        supabase.table("alunos")
        .update({"status": novo_status})
        .eq("id", str(aluno_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Aluno não encontrado"}), 404
    return jsonify(result.data[0])


# ── Vínculos aluno ↔ plano ────────────────────────────────────────────────────

@alunos_bp.get("/<uuid:aluno_id>/planos")
@require_auth
def listar_planos(aluno_id):
    result = (
        supabase.table("aluno_planos")
        .select("*, planos(nome, valor, duracao_dias)")
        .eq("aluno_id", str(aluno_id))
        .execute()
    )
    return jsonify(result.data)


@alunos_bp.post("/<uuid:aluno_id>/planos")
@require_role("admin", "recepcionista")
def vincular_plano(aluno_id):
    data = request.get_json(silent=True) or {}

    for campo in ("plano_id", "data_inicio"):
        if not data.get(campo):
            return jsonify({"error": f"Campo '{campo}' é obrigatório"}), 400

    # Busca o valor do plano para gerar a primeira mensalidade
    plano = (
        supabase.table("planos")
        .select("valor")
        .eq("id", data["plano_id"])
        .single()
        .execute()
    )
    if not plano.data:
        return jsonify({"error": "Plano não encontrado"}), 404

    vínculo = supabase.table("aluno_planos").insert({
        "aluno_id": str(aluno_id),
        "plano_id": data["plano_id"],
        "data_inicio": data["data_inicio"],
        "data_fim": data.get("data_fim"),
    }).execute()

    aluno_plano_id = vínculo.data[0]["id"]

    # Gera a primeira mensalidade com vencimento na data de início
    from ..mensalidades.jobs import criar_mensalidade
    criar_mensalidade(
        aluno_plano_id,
        plano.data["valor"],
        date.fromisoformat(data["data_inicio"]),
    )

    return jsonify(vínculo.data[0]), 201


@alunos_bp.delete("/<uuid:aluno_id>/planos/<uuid:aluno_plano_id>")
@require_role("admin", "recepcionista")
def cancelar_plano(aluno_id, aluno_plano_id):
    result = (
        supabase.table("aluno_planos")
        .update({"status": "cancelado"})
        .eq("id", str(aluno_plano_id))
        .eq("aluno_id", str(aluno_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Vínculo não encontrado"}), 404
    return jsonify({"message": "Plano cancelado com sucesso"})

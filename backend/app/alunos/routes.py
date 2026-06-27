import re
from flask import Blueprint, request, jsonify, g, current_app
from ..supabase_client import supabase, get_user_client
from ..auth.middleware import require_auth, require_role
from ..schemas import (
    AlunoCreateSchema,
    AlunoUpdateSchema,
    AlunoStatusSchema,
    VincularPlanoAlunoSchema,
)
from ..validation import validate_body
from ..errors import email_ja_cadastrado

alunos_bp = Blueprint("alunos", __name__, url_prefix="/alunos")


# ── Alunos ────────────────────────────────────────────────────────────────────

@alunos_bp.get("")
@require_role("admin", "recepcionista")
def listar():
    status = request.args.get("status")   # ativo | inativo | inadimplente
    cpf = request.args.get("cpf")

    query = supabase.table("alunos").select("*, profiles(nome, telefone)")

    if status in ("ativo", "inativo", "inadimplente"):
        query = query.eq("status", status)
    if cpf:
        cpf_limpo = re.sub(r"\D", "", cpf)
        query = query.eq("cpf", cpf_limpo)

    result = query.order("created_at", desc=True).execute()
    return jsonify(result.data)


@alunos_bp.post("")
@require_role("admin", "recepcionista")
@validate_body(AlunoCreateSchema)
def criar(payload: AlunoCreateSchema):
    # 1. Cria usuário no Supabase Auth (trigger cria o profile automaticamente)
    try:
        user_resp = supabase.auth.admin.create_user({
            "email": payload.email,
            "password": payload.senha,
            "email_confirm": True,
            "user_metadata": {"nome": payload.nome, "tipo": "aluno"},
        })
        user_id = user_resp.user.id
    except Exception as e:
        current_app.logger.exception("Falha ao criar usuário no Supabase Auth")
        msg = "E-mail já cadastrado" if email_ja_cadastrado(e) else "Não foi possível criar o usuário"
        return jsonify({"error": msg}), 400

    # 2. Atualiza telefone no profile (o trigger só popula nome e tipo)
    if payload.telefone:
        supabase.table("profiles").update({"telefone": payload.telefone}).eq("id", user_id).execute()

    # 3. Cria registro do aluno vinculado ao profile
    try:
        aluno_resp = supabase.table("alunos").insert({
            "profile_id": user_id,
            "cpf": payload.cpf,
            "data_nascimento": payload.data_nascimento.isoformat() if payload.data_nascimento else None,
            "endereco": payload.endereco,
            "status": payload.status,
            "frequencia_habilitada": payload.frequencia_habilitada,
        }).execute()
        return jsonify(aluno_resp.data[0]), 201
    except Exception:
        # Rollback: remove o usuário criado se o aluno falhar
        supabase.auth.admin.delete_user(user_id)
        current_app.logger.exception("Falha ao salvar aluno; usuário do Auth revertido")
        return jsonify({"error": "Não foi possível salvar o aluno"}), 400


@alunos_bp.get("/<uuid:aluno_id>")
@require_auth
def buscar(aluno_id):
    # Cliente sob a identidade do usuário: a RLS decide se ele pode ver este
    # aluno (admin/recepcionista veem todos; instrutor só os dos seus planos;
    # aluno só a si mesmo). Mitiga BOLA/IDOR — antes a service_role devolvia
    # qualquer aluno para qualquer autenticado.
    db = get_user_client(g.access_token)
    result = (
        db.table("alunos")
        .select("*, profiles(nome, telefone), aluno_planos(id, status, data_inicio, data_fim, planos(nome, valor))")
        .eq("id", str(aluno_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Aluno não encontrado"}), 404
    return jsonify(result.data)


@alunos_bp.put("/<uuid:aluno_id>")
@require_role("admin", "recepcionista")
@validate_body(AlunoUpdateSchema)
def atualizar(aluno_id, payload: AlunoUpdateSchema):
    update = payload.model_dump(exclude_unset=True)

    # telefone vai para profiles, não para alunos
    telefone = update.pop("telefone", None)

    # cpf não pode ser apagado (NOT NULL/UNIQUE no banco)
    if update.get("cpf") is None:
        update.pop("cpf", None)
    if update.get("data_nascimento") is not None:
        update["data_nascimento"] = update["data_nascimento"].isoformat()

    if not update and telefone is None:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    # Busca o profile_id do aluno para atualizar profiles
    if telefone is not None:
        aluno_row = (
            supabase.table("alunos")
            .select("profile_id")
            .eq("id", str(aluno_id))
            .maybe_single()
            .execute()
        )
        if not aluno_row or not aluno_row.data:
            return jsonify({"error": "Aluno não encontrado"}), 404
        supabase.table("profiles").update({"telefone": telefone}).eq("id", aluno_row.data["profile_id"]).execute()

    if not update:
        aluno_row = aluno_row if telefone is not None else None
        if aluno_row and aluno_row.data:
            return jsonify({"message": "Perfil atualizado com sucesso"}), 200
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
@validate_body(AlunoStatusSchema)
def atualizar_status(aluno_id, payload: AlunoStatusSchema):
    result = (
        supabase.table("alunos")
        .update({"status": payload.status})
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
    # RLS por identidade: admin/recepcionista veem todos; aluno só os próprios.
    db = get_user_client(g.access_token)
    result = (
        db.table("aluno_planos")
        .select("*, planos(nome, valor, duracao_dias)")
        .eq("aluno_id", str(aluno_id))
        .execute()
    )
    return jsonify(result.data)


@alunos_bp.post("/<uuid:aluno_id>/planos")
@require_role("admin", "recepcionista")
@validate_body(VincularPlanoAlunoSchema)
def vincular_plano(aluno_id, payload: VincularPlanoAlunoSchema):
    # Busca o valor do plano para gerar a primeira mensalidade
    plano = (
        supabase.table("planos")
        .select("valor")
        .eq("id", str(payload.plano_id))
        .single()
        .execute()
    )
    if not plano.data:
        return jsonify({"error": "Plano não encontrado"}), 404

    vinculo = supabase.table("aluno_planos").insert({
        "aluno_id": str(aluno_id),
        "plano_id": str(payload.plano_id),
        "data_inicio": payload.data_inicio.isoformat(),
        "data_fim": payload.data_fim.isoformat() if payload.data_fim else None,
    }).execute()

    aluno_plano_id = vinculo.data[0]["id"]

    # Gera a primeira mensalidade com vencimento na data de início
    from ..mensalidades.jobs import criar_mensalidade
    criar_mensalidade(aluno_plano_id, plano.data["valor"], payload.data_inicio)

    return jsonify(vinculo.data[0]), 201


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

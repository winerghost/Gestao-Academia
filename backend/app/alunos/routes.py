import re
from flask import Blueprint, request, jsonify, g, current_app
from ..supabase_client import supabase, get_user_client
from ..auth.middleware import require_auth, require_role
from ..schemas import (
    AlunoCreateSchema,
    AlunoUpdateSchema,
    AlunoStatusSchema,
    VincularPlanoAlunoSchema,
    AlunoPlanoUpdateSchema,
)
from ..validation import validate_body
from ..errors import email_ja_cadastrado, violacao_unicidade
from ..auth.avatar import (
    AvatarError,
    processar_imagem_base64,
    upload_avatar,
    url_gravatar,
    gravatar_existe,
)

alunos_bp = Blueprint("alunos", __name__, url_prefix="/alunos")

_LIMITES_VALIDOS = frozenset({25, 50, 100, 200})


# ── Alunos ────────────────────────────────────────────────────────────────────

@alunos_bp.get("")
@require_role("admin", "recepcionista")
def listar():
    status = request.args.get("status")   # ativo | inativo | inadimplente
    cpf    = request.args.get("cpf")
    busca  = request.args.get("busca", "").strip()

    try:
        limit  = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except (ValueError, TypeError):
        limit, offset = 50, 0

    if limit not in _LIMITES_VALIDOS:
        limit = 50
    offset = max(0, offset)

    query = supabase.table("alunos").select("*, profiles(nome, telefone)", count="exact")

    if status in ("ativo", "inativo", "inadimplente"):
        query = query.eq("status", status)
    if cpf:
        query = query.eq("cpf", re.sub(r"\D", "", cpf))
    if busca:
        if re.fullmatch(r"\d+", re.sub(r"\D", "", busca)) and not re.search(r"[A-Za-zÀ-ÿ]", busca):
            # somente dígitos → busca por CPF parcial
            query = query.ilike("cpf", f"%{re.sub(r'[^0-9]', '', busca)}%")
        else:
            # texto → busca por nome no profile relacionado
            query = query.filter("profiles.nome", "ilike", f"%{busca}%")

    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return jsonify({
        "data":   result.data,
        "total":  result.count,
        "limit":  limit,
        "offset": offset,
    })


@alunos_bp.post("")
@require_role("admin", "recepcionista")
@validate_body(AlunoCreateSchema)
def criar(payload: AlunoCreateSchema):
    # 0. Valida/processa a foto ANTES de criar o usuário: assim uma imagem
    #    inválida não deixa um usuário órfão no Auth. O Pillow re-encoda
    #    (descarta EXIF/payloads) — sanitização no backend.
    foto_jpeg = None
    if payload.foto:
        try:
            foto_jpeg = processar_imagem_base64(payload.foto)
        except AvatarError as e:
            return jsonify({"error": str(e)}), 400

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

    # 2. Define o avatar: o Gravatar PREVALECE sobre a foto da webcam. Checamos
    #    o Gravatar em todo cadastro (o e-mail sempre existe), então um aluno com
    #    Gravatar ganha o avatar automático mesmo sem foto. Se não houver
    #    Gravatar e houver foto, subimos a foto. Falha aqui não derruba o
    #    cadastro — o aluno fica sem foto (iniciais).
    avatar_url = None
    try:
        if gravatar_existe(payload.email):
            avatar_url = url_gravatar(payload.email)
        elif foto_jpeg:
            avatar_url = upload_avatar(supabase, user_id, foto_jpeg)
    except Exception:
        current_app.logger.exception("Falha ao definir avatar do aluno no cadastro")

    # 3. Atualiza o profile (telefone + avatar_url numa só escrita; o trigger
    #    só popula nome e tipo).
    prof_update = {}
    if payload.telefone:
        prof_update["telefone"] = payload.telefone
    if avatar_url:
        prof_update["avatar_url"] = avatar_url
    if prof_update:
        supabase.table("profiles").update(prof_update).eq("id", user_id).execute()

    # 4. Cria registro do aluno vinculado ao profile
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
        .select("*, profiles(nome, telefone, avatar_url), aluno_planos(id, plano_id, status, data_inicio, data_fim, planos(nome, valor))")
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

    # Regra de negócio: um aluno não pode ter o MESMO plano ativo mais de uma
    # vez. Checamos na aplicação para devolver uma mensagem amigável (409); o
    # índice único parcial `uq_aluno_planos_ativo` (migration 011) é a garantia
    # definitiva contra corridas e é tratado no except abaixo.
    ja_ativo = (
        supabase.table("aluno_planos")
        .select("id")
        .eq("aluno_id", str(aluno_id))
        .eq("plano_id", str(payload.plano_id))
        .eq("status", "ativo")
        .limit(1)
        .execute()
    )
    if ja_ativo.data:
        return jsonify({"error": "Este plano já está vinculado e ativo para este aluno."}), 409

    try:
        vinculo = supabase.table("aluno_planos").insert({
            "aluno_id": str(aluno_id),
            "plano_id": str(payload.plano_id),
            "data_inicio": payload.data_inicio.isoformat(),
            "data_fim": payload.data_fim.isoformat() if payload.data_fim else None,
        }).execute()
    except Exception as e:
        if violacao_unicidade(e):
            return jsonify({"error": "Este plano já está vinculado e ativo para este aluno."}), 409
        raise

    aluno_plano_id = vinculo.data[0]["id"]

    # Gera a primeira mensalidade com vencimento na data de início (idempotente)
    from ..mensalidades.jobs import criar_mensalidade
    criar_mensalidade(aluno_plano_id, plano.data["valor"], payload.data_inicio)

    return jsonify(vinculo.data[0]), 201


@alunos_bp.get("/<uuid:aluno_id>/planos/<uuid:aluno_plano_id>")
@require_auth
def detalhe_plano(aluno_id, aluno_plano_id):
    # Detalhes do vínculo + plano + suas mensalidades. RLS por identidade
    # (admin/recepcionista veem todos; aluno só os próprios).
    db = get_user_client(g.access_token)
    result = (
        db.table("aluno_planos")
        .select("*, planos(nome, valor, duracao_dias), "
                "mensalidades(id, valor, juros, valor_total, data_vencimento, data_pagamento, status)")
        .eq("id", str(aluno_plano_id))
        .eq("aluno_id", str(aluno_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Vínculo não encontrado"}), 404
    return jsonify(result.data)


@alunos_bp.put("/<uuid:aluno_id>/planos/<uuid:aluno_plano_id>")
@require_role("admin", "recepcionista")
@validate_body(AlunoPlanoUpdateSchema)
def editar_plano(aluno_id, aluno_plano_id, payload: AlunoPlanoUpdateSchema):
    update = payload.model_dump(exclude_unset=True)

    # data_inicio é NOT NULL: um valor vazio (None) não pode ir para o banco,
    # então é descartado (mantém o valor atual) em vez de virar um 500.
    if update.get("data_inicio") is None:
        update.pop("data_inicio", None)

    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    for campo in ("data_inicio", "data_fim"):
        if campo in update and update[campo] is not None:
            update[campo] = update[campo].isoformat()

    try:
        result = (
            supabase.table("aluno_planos")
            .update(update)
            .eq("id", str(aluno_plano_id))
            .eq("aluno_id", str(aluno_id))
            .execute()
        )
    except Exception as e:
        # Reativar um vínculo (status='ativo') quando já existe outro ativo do
        # mesmo plano colide com o índice único parcial → 409 amigável.
        if violacao_unicidade(e):
            return jsonify({"error": "Já existe um vínculo ativo deste plano para o aluno."}), 409
        raise

    if not result.data:
        return jsonify({"error": "Vínculo não encontrado"}), 404
    return jsonify(result.data[0])


@alunos_bp.delete("/<uuid:aluno_id>/planos/<uuid:aluno_plano_id>")
@require_role("admin", "recepcionista")
def remover_plano(aluno_id, aluno_plano_id):
    """Remove um vínculo aluno↔plano.

    Dois modos (querystring `permanente`):
      - padrão (cancelar): soft-delete → status='cancelado'. Preserva o
        histórico (vínculo e mensalidades permanecem no banco).
      - `?permanente=true` (excluir): exclusão física. BLOQUEIA se houver
        qualquer mensalidade PAGA (preserva histórico financeiro); caso só
        existam pendentes/atrasadas, exclui o vínculo e elas em cascata
        (FK ON DELETE CASCADE).
    """
    permanente = request.args.get("permanente", "").lower() in ("1", "true", "sim")

    # Garante que o vínculo existe e pertence ao aluno (evita 200 enganoso).
    vinculo = (
        supabase.table("aluno_planos")
        .select("id")
        .eq("id", str(aluno_plano_id))
        .eq("aluno_id", str(aluno_id))
        .maybe_single()
        .execute()
    )
    if not vinculo or not vinculo.data:
        return jsonify({"error": "Vínculo não encontrado"}), 404

    if not permanente:
        supabase.table("aluno_planos").update({"status": "cancelado"}).eq(
            "id", str(aluno_plano_id)
        ).execute()
        return jsonify({"message": "Plano cancelado com sucesso"})

    # Exclusão física: barra se houver mensalidade paga.
    mensalidades = (
        supabase.table("mensalidades")
        .select("status")
        .eq("aluno_plano_id", str(aluno_plano_id))
        .execute()
    )
    if any(m["status"] == "paga" for m in (mensalidades.data or [])):
        return jsonify({
            "error": "Não é possível excluir: há mensalidade(s) paga(s) neste vínculo. "
                     "Use 'Cancelar' para preservar o histórico financeiro."
        }), 409

    supabase.table("aluno_planos").delete().eq("id", str(aluno_plano_id)).execute()
    return jsonify({"message": "Vínculo excluído com sucesso"})

from datetime import datetime, timezone

from flask import Blueprint, jsonify, g, request, current_app
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role
from ..schemas import (
    AcademiaConfigSchema,
    UserTipoSchema,
    UserStatusSchema,
    CriarUsuarioSchema,
    ResetSenhaAdminSchema,
)
from ..validation import validate_body
from ..errors import email_ja_cadastrado
from ..auth.avatar import (
    AvatarError,
    processar_imagem,
    processar_imagem_base64,
    upload_avatar,
    remover_avatares_storage,
)

configuracoes_bp = Blueprint("configuracoes", __name__, url_prefix="/configuracoes")

# A configuração da academia mora numa única linha (id = 1).
_CONFIG_ID = 1


def _ler_config():
    return (
        supabase.table("academia_config")
        .select("*")
        .eq("id", _CONFIG_ID)
        .single()
        .execute()
    )


@configuracoes_bp.get("/usuarios")
@require_role("admin")
def listar_usuarios():
    """Lista todos os profiles com email do Supabase Auth (somente admin)."""
    busca = request.args.get("busca", "").strip().lower()

    # select("*") tolera a coluna `ativo` ainda não migrada (default no .get).
    profiles_result = (
        supabase.table("profiles")
        .select("*")
        .order("created_at")
        .execute()
    )
    profiles = {p["id"]: p for p in (profiles_result.data or [])}

    auth_users = supabase.auth.admin.list_users()
    user_list = auth_users if isinstance(auth_users, list) else []

    result = []
    for u in user_list:
        uid = str(u.id)
        profile = profiles.get(uid)
        if profile:
            result.append({
                "id": uid,
                "email": u.email,
                "nome": profile["nome"],
                "tipo": profile["tipo"],
                "telefone": profile.get("telefone"),
                "ativo": profile.get("ativo", True),
                "avatar_url": profile.get("avatar_url"),
                "created_at": profile["created_at"],
            })

    if busca:
        result = [
            u for u in result
            if busca in (u["nome"] or "").lower()
            or busca in (u["email"] or "").lower()
        ]

    return jsonify(result)


@configuracoes_bp.post("/usuarios")
@require_role("admin")
@validate_body(CriarUsuarioSchema)
def criar_usuario(payload: CriarUsuarioSchema):
    """Cria um novo usuário do sistema (somente admin). Alunos usam o fluxo próprio (CPF obrigatório)."""
    # 0. Processa a foto ANTES de criar o usuário Auth: imagem inválida não deixa
    #    um usuário órfão caso o upload do avatar falhe depois.
    foto_jpeg = None
    if payload.foto:
        try:
            foto_jpeg = processar_imagem_base64(payload.foto)
        except AvatarError as exc:
            return jsonify({"error": str(exc)}), 400

    # 1. Cria o usuário no Supabase Auth; o trigger cria o profile automaticamente.
    try:
        user_resp = supabase.auth.admin.create_user({
            "email": payload.email,
            "password": payload.senha,
            "email_confirm": True,  # dispensa e-mail de confirmação (criação pelo admin)
            "user_metadata": {"nome": payload.nome, "tipo": payload.tipo},
        })
        user_id = str(user_resp.user.id)
    except Exception as exc:
        current_app.logger.exception("Falha ao criar usuário no Supabase Auth")
        msg = "E-mail já cadastrado" if email_ja_cadastrado(exc) else "Não foi possível criar o usuário"
        return jsonify({"error": msg}), 400

    # 2. Atualiza o profile: telefone e avatar_url (o trigger só popula nome e tipo).
    avatar_url = None
    prof_update = {}
    if payload.telefone:
        prof_update["telefone"] = payload.telefone

    if foto_jpeg:
        try:
            avatar_url = upload_avatar(supabase, user_id, foto_jpeg)
            prof_update["avatar_url"] = avatar_url
        except Exception:
            current_app.logger.exception("Falha ao fazer upload da foto na criação de usuário")

    if prof_update:
        supabase.table("profiles").update(prof_update).eq("id", user_id).execute()

    # 3. Se instrutor, garante registro na tabela instrutores.
    if payload.tipo == "instrutor":
        supabase.table("instrutores").insert({"profile_id": user_id}).execute()

    return jsonify({
        "id": user_id,
        "email": payload.email,
        "nome": payload.nome,
        "tipo": payload.tipo,
        "telefone": payload.telefone,
        "ativo": True,
        "avatar_url": avatar_url,
    }), 201


@configuracoes_bp.delete("/usuarios/<user_id>")
@require_role("admin")
def excluir_usuario(user_id):
    """Exclui permanentemente um usuário do sistema (somente admin).

    Bloqueios:
    - Si mesmo / último admin: sempre bloqueado.
    - Aluno com mensalidades em atraso: deve regularizar os débitos primeiro.
    - Aluno com histórico financeiro (pagas/pendentes): use Desativar para
      preservar o histórico. Só permite exclusão quando não há mensalidades.
    """
    uid = str(user_id)

    if uid == str(g.user_id):
        return jsonify({"error": "Você não pode excluir sua própria conta"}), 400

    admins_res = supabase.table("profiles").select("id").eq("tipo", "admin").execute()
    admin_ids = [p["id"] for p in (admins_res.data or [])]
    if uid in admin_ids and len(admin_ids) <= 1:
        return jsonify({"error": "Não é possível excluir o único administrador do sistema"}), 400

    # Para alunos: verifica o histórico de mensalidades antes de permitir exclusão.
    sit = _mensalidades_aluno(uid)
    if sit == "atrasada":
        return jsonify({
            "error": "O aluno possui mensalidades em atraso. "
                     "Regularize os débitos antes de excluir a conta."
        }), 409
    if sit == "historico":
        return jsonify({
            "error": "O aluno possui histórico de mensalidades. "
                     "Use Desativar para bloquear o acesso sem perder o histórico financeiro."
        }), 409

    try:
        supabase.auth.admin.delete_user(uid)
    except Exception:
        current_app.logger.exception("Falha ao excluir usuário do Supabase Auth")
        return jsonify({"error": "Não foi possível excluir o usuário"}), 400

    return "", 204


@configuracoes_bp.post("/usuarios/<user_id>/reset-senha")
@require_role("admin")
@validate_body(ResetSenhaAdminSchema)
def reset_senha_usuario(user_id: str, payload: ResetSenhaAdminSchema):
    """Admin redefine a senha de qualquer usuário (somente admin).

    O admin não precisa conhecer a senha atual — usa a Admin API do Supabase.
    Bloqueado para o próprio admin: use /auth/change-password para isso.
    """
    uid = str(user_id)
    if uid == str(g.user_id):
        return jsonify({
            "error": "Use a tela Conta para alterar sua própria senha."
        }), 400

    try:
        supabase.auth.admin.update_user_by_id(uid, {"password": payload.senha_nova})
    except Exception:
        current_app.logger.exception("Falha ao redefinir senha do usuário %s", uid)
        return jsonify({"error": "Não foi possível redefinir a senha. Verifique se o usuário existe."}), 400

    return "", 204


@configuracoes_bp.patch("/usuarios/<user_id>/tipo")
@require_role("admin")
@validate_body(UserTipoSchema)
def atualizar_tipo_usuario(user_id: str, payload: UserTipoSchema):
    """Altera o papel de um usuário (somente admin; não pode alterar o próprio)."""
    if user_id == str(g.user_id):
        return jsonify({"error": "Você não pode alterar seu próprio tipo"}), 400

    result = (
        supabase.table("profiles")
        .update({"tipo": payload.tipo})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Usuário não encontrado"}), 404

    # Quando promovido a instrutor via Kanban, garante registro na tabela instrutores.
    # Todos os campos específicos (especialidade, salario, etc.) ficam nulos e podem
    # ser preenchidos depois na tela de edição do instrutor.
    if payload.tipo == "instrutor":
        existing = (
            supabase.table("instrutores")
            .select("id")
            .eq("profile_id", user_id)
            .maybe_single()
            .execute()
        )
        if not existing.data:
            supabase.table("instrutores").insert({"profile_id": user_id}).execute()

    return jsonify(result.data[0])


@configuracoes_bp.patch("/usuarios/<user_id>/status")
@require_role("admin")
@validate_body(UserStatusSchema)
def atualizar_status_usuario(user_id: str, payload: UserStatusSchema):
    """Ativa/desativa um usuário (somente admin; não pode desativar a si mesmo).

    Ao desativar um aluno: bloqueado se houver mensalidades em atraso.
    Reativação: sempre permitida, independentemente do histórico.
    """
    if user_id == str(g.user_id):
        return jsonify({"error": "Você não pode desativar sua própria conta"}), 400

    # Ao desativar, verifica débitos pendentes (apenas para alunos).
    if not payload.ativo:
        sit = _mensalidades_aluno(user_id)
        if sit == "atrasada":
            return jsonify({
                "error": "O aluno possui mensalidades em atraso. "
                         "Regularize os débitos antes de desativar a conta."
            }), 409

    result = (
        supabase.table("profiles")
        .update({"ativo": payload.ativo})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Usuário não encontrado"}), 404

    return jsonify(result.data[0])


def _mensalidades_aluno(uid: str):
    """Inspeciona o histórico de mensalidades de um usuário que seja aluno.

    Retorna:
      'atrasada'  — tem ao menos uma mensalidade com status 'atrasada'
      'historico' — tem mensalidades (pagas ou pendentes), mas nenhuma atrasada
      None        — não é aluno OU é aluno sem nenhuma mensalidade
    """
    aluno = (
        supabase.table("alunos")
        .select("id")
        .eq("profile_id", uid)
        .maybe_single()
        .execute()
    )
    if not aluno.data:
        return None  # usuário não é aluno

    aluno_id = aluno.data["id"]
    planos = (
        supabase.table("aluno_planos")
        .select("id")
        .eq("aluno_id", aluno_id)
        .execute()
    )
    plano_ids = [p["id"] for p in (planos.data or [])]
    if not plano_ids:
        return None  # aluno sem planos vinculados

    # Verifica atrasadas primeiro (prioridade maior)
    atrasadas = (
        supabase.table("mensalidades")
        .select("id")
        .in_("aluno_plano_id", plano_ids)
        .eq("status", "atrasada")
        .limit(1)
        .execute()
    )
    if atrasadas.data:
        return "atrasada"

    # Verifica se existe qualquer mensalidade (preservar histórico financeiro)
    qualquer = (
        supabase.table("mensalidades")
        .select("id")
        .in_("aluno_plano_id", plano_ids)
        .limit(1)
        .execute()
    )
    if qualquer.data:
        return "historico"

    return None


def _profile_existe(user_id: str) -> bool:
    prof = (
        supabase.table("profiles")
        .select("id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return bool(prof and prof.data)


@configuracoes_bp.post("/usuarios/<uuid:user_id>/avatar")
@require_role("admin", "recepcionista")
def definir_avatar_usuario(user_id):
    """Admin/recepcionista define a foto de qualquer usuário (ex.: um aluno).

    Mesma sanitização do autoatendimento: a imagem é re-encodada com Pillow
    antes de ir ao Storage. O path usa o id do ALVO (`<user_id>/...`).
    """
    if not _profile_existe(str(user_id)):
        return jsonify({"error": "Usuário não encontrado"}), 404

    arquivo = request.files.get("file")
    if arquivo is None or not arquivo.filename:
        return jsonify({"error": "Nenhum arquivo enviado (campo 'file')."}), 400

    try:
        jpeg = processar_imagem(arquivo.read())
    except AvatarError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        url = upload_avatar(supabase, str(user_id), jpeg)
    except Exception:  # noqa: BLE001 — falha de Storage vira 502 amigável
        current_app.logger.exception("Falha ao enviar avatar de usuário")
        return jsonify({"error": "Não foi possível enviar a foto. Tente novamente."}), 502

    supabase.table("profiles").update({"avatar_url": url}).eq("id", str(user_id)).execute()
    return jsonify({"avatar_url": url})


@configuracoes_bp.delete("/usuarios/<uuid:user_id>/avatar")
@require_role("admin", "recepcionista")
def remover_avatar_usuario(user_id):
    """Admin/recepcionista remove a foto de qualquer usuário."""
    if not _profile_existe(str(user_id)):
        return jsonify({"error": "Usuário não encontrado"}), 404

    try:
        remover_avatares_storage(supabase, str(user_id))
    except Exception:  # noqa: BLE001 — mesmo se o Storage falhar, limpamos a referência
        current_app.logger.exception("Falha ao remover avatar de usuário")

    supabase.table("profiles").update({"avatar_url": None}).eq("id", str(user_id)).execute()
    return jsonify({"avatar_url": None})


@configuracoes_bp.get("/academia")
@require_auth
def obter_academia():
    """Configuração da academia — qualquer usuário autenticado pode ler."""
    result = _ler_config()
    return jsonify(result.data)


@configuracoes_bp.put("/academia")
@require_role("admin")
@validate_body(AcademiaConfigSchema)
def atualizar_academia(payload: AcademiaConfigSchema):
    """Atualiza dados cadastrais, horários e notificações (somente admin)."""
    update = payload.model_dump(exclude_unset=True)
    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("academia_config")
        .update(update)
        .eq("id", _CONFIG_ID)
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Configuração não encontrada"}), 404
    return jsonify(result.data[0])

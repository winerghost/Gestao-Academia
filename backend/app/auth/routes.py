from flask import Blueprint, jsonify, g, request, current_app
from gotrue.errors import AuthApiError
from ..supabase_client import supabase, get_anon_client
from ..extensions import limiter
from ..config import Config
from ..schemas import LoginSchema, ProfileUpdateSchema, ChangePasswordSchema
from ..validation import validate_body
from ..errors import erro_campo
from .middleware import require_auth, _get_token
from .avatar import (
    AvatarError,
    processar_imagem,
    upload_avatar,
    remover_avatares_storage,
    url_gravatar,
    gravatar_existe,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/login")
@limiter.limit(lambda: Config.RATELIMIT_LOGIN)
@validate_body(LoginSchema)
def login(payload: LoginSchema):
    # Cliente anon isolado por requisição: a sessão fica contida aqui e
    # nunca contamina o cliente global de service role.
    client = get_anon_client()
    try:
        response = client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except AuthApiError:
        return jsonify({"error": "Credenciais inválidas"}), 401

    # Conta desativada não loga, mesmo com a senha correta.
    # select("*") tolera a coluna `ativo` ainda não migrada (trata como ativo).
    profile = (
        supabase.table("profiles")
        .select("*")
        .eq("id", response.user.id)
        .maybe_single()
        .execute()
    )
    if profile and profile.data and not profile.data.get("ativo", True):
        return jsonify({"error": "Conta desativada. Procure o administrador."}), 403

    return jsonify({
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "user": {
            "id": response.user.id,
            "email": response.user.email,
        },
    })


@auth_bp.post("/logout")
@require_auth
def logout():
    token = _get_token()
    # Revoga a sessão deste token via Admin API (header service role, sem
    # gravar estado no cliente global). scope="local" invalida apenas esta
    # sessão; as demais sessões do usuário continuam válidas.
    try:
        supabase.auth.admin.sign_out(token, scope="local")
    except AuthApiError:
        pass
    return jsonify({"message": "Logout realizado com sucesso"})


@auth_bp.get("/me")
@require_auth
def me():
    """Retorna o perfil do usuário logado."""
    result = (
        supabase.table("profiles")
        .select("id, nome, tipo, telefone, preferencias, avatar_url, created_at")
        .eq("id", g.user_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Perfil não encontrado"}), 404
    return jsonify(result.data)


@auth_bp.put("/me")
@require_auth
@validate_body(ProfileUpdateSchema)
def atualizar_me(payload: ProfileUpdateSchema):
    """Atualiza o próprio perfil: nome, telefone e preferências de aparência."""
    update = payload.model_dump(exclude_unset=True)
    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    result = (
        supabase.table("profiles")
        .update(update)
        .eq("id", g.user_id)
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Perfil não encontrado"}), 404
    return jsonify(result.data[0])


@auth_bp.post("/change-password")
@require_auth
@validate_body(ChangePasswordSchema)
def trocar_senha(payload: ChangePasswordSchema):
    """Troca a senha do usuário logado.

    Confirma a senha atual fazendo um login isolado (cliente anon sem estado)
    antes de gravar a nova senha via Admin API — assim ninguém troca a senha
    de outra pessoa só com um token válido roubado/compartilhado.
    """
    # Descobre o e-mail do usuário (necessário para revalidar a senha atual).
    try:
        user = supabase.auth.admin.get_user_by_id(g.user_id).user
    except AuthApiError:
        return jsonify({"error": "Usuário não encontrado"}), 404
    email = user.email

    # Revalida a senha atual num cliente isolado (não toca o cliente global).
    client = get_anon_client()
    try:
        client.auth.sign_in_with_password(
            {"email": email, "password": payload.senha_atual}
        )
    except AuthApiError:
        return erro_campo("senha_atual", "Senha atual incorreta.", 400)

    if payload.senha_nova == payload.senha_atual:
        return erro_campo("senha_nova", "A nova senha deve ser diferente da atual.", 400)

    # Grava a nova senha via Admin API.
    try:
        supabase.auth.admin.update_user_by_id(
            g.user_id, {"password": payload.senha_nova}
        )
    except AuthApiError:
        return jsonify({"error": "Não foi possível alterar a senha"}), 400

    return jsonify({"message": "Senha alterada com sucesso"})


# ── Foto de perfil (avatar) ──────────────────────────────────────────────────

@auth_bp.post("/me/avatar")
@require_auth
def enviar_avatar():
    """Recebe a foto (multipart, campo 'file'), re-encoda e sobe ao Storage.

    A imagem é sempre reprocessada com Pillow antes de salvar (descarta EXIF e
    payloads embutidos). Guarda a URL pública resultante em profiles.avatar_url.
    """
    arquivo = request.files.get("file")
    if arquivo is None or not arquivo.filename:
        return jsonify({"error": "Nenhum arquivo enviado (campo 'file')."}), 400

    try:
        jpeg = processar_imagem(arquivo.read())
    except AvatarError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        url = upload_avatar(supabase, str(g.user_id), jpeg)
    except Exception:  # noqa: BLE001 — falha de rede/Storage vira 502 amigável
        current_app.logger.exception("Falha ao enviar avatar para o Storage")
        return jsonify({"error": "Não foi possível enviar a foto. Tente novamente."}), 502

    supabase.table("profiles").update({"avatar_url": url}).eq("id", g.user_id).execute()
    return jsonify({"avatar_url": url})


@auth_bp.delete("/me/avatar")
@require_auth
def remover_avatar():
    """Remove a foto: apaga do Storage e zera avatar_url (volta às iniciais)."""
    try:
        remover_avatares_storage(supabase, str(g.user_id))
    except Exception:  # noqa: BLE001 — mesmo se o Storage falhar, limpamos a referência
        current_app.logger.exception("Falha ao remover avatar do Storage")

    supabase.table("profiles").update({"avatar_url": None}).eq("id", g.user_id).execute()
    return jsonify({"avatar_url": None})


@auth_bp.post("/me/avatar/gravatar")
@require_auth
def usar_gravatar():
    """Usa o Gravatar do e-mail do próprio usuário como foto de perfil.

    O e-mail vem do Supabase Auth (backend), não do cliente — assim ninguém
    aponta o avatar para o Gravatar de outra pessoa. Só grava se o Gravatar
    realmente existir para aquele e-mail.
    """
    try:
        user = supabase.auth.admin.get_user_by_id(g.user_id).user
    except AuthApiError:
        return jsonify({"error": "Usuário não encontrado"}), 404

    email = user.email if user else None
    if not email or not gravatar_existe(email):
        return jsonify({"error": "Não encontramos um Gravatar para o seu e-mail."}), 404

    url = url_gravatar(email)
    # Passou a usar o Gravatar → descarta qualquer foto enviada que estava no Storage.
    try:
        remover_avatares_storage(supabase, str(g.user_id))
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Falha ao limpar Storage ao ativar Gravatar")

    supabase.table("profiles").update({"avatar_url": url}).eq("id", g.user_id).execute()
    return jsonify({"avatar_url": url})

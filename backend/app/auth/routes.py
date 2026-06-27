from flask import Blueprint, jsonify, g
from gotrue.errors import AuthApiError
from ..supabase_client import supabase, get_anon_client
from ..extensions import limiter
from ..config import Config
from ..schemas import LoginSchema, ProfileUpdateSchema, ChangePasswordSchema
from ..validation import validate_body
from .middleware import require_auth, _get_token

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
        .single()
        .execute()
    )
    if profile.data and not profile.data.get("ativo", True):
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
        .select("id, nome, tipo, telefone, preferencias, created_at")
        .eq("id", g.user_id)
        .single()
        .execute()
    )
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
        return jsonify({"error": "Senha atual incorreta"}), 400

    if payload.senha_nova == payload.senha_atual:
        return jsonify({"error": "A nova senha deve ser diferente da atual"}), 400

    # Grava a nova senha via Admin API.
    try:
        supabase.auth.admin.update_user_by_id(
            g.user_id, {"password": payload.senha_nova}
        )
    except AuthApiError:
        return jsonify({"error": "Não foi possível alterar a senha"}), 400

    return jsonify({"message": "Senha alterada com sucesso"})

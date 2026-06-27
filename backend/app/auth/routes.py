from flask import Blueprint, jsonify, g
from gotrue.errors import AuthApiError
from ..supabase_client import supabase, get_anon_client
from ..extensions import limiter
from ..config import Config
from ..schemas import LoginSchema
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
        .select("id, nome, tipo, telefone, created_at")
        .eq("id", g.user_id)
        .single()
        .execute()
    )
    return jsonify(result.data)

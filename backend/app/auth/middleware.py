from functools import wraps
import httpx
from flask import request, jsonify, g
from gotrue.errors import AuthApiError
from ..supabase_client import supabase


def _with_retry(fn, retries: int = 1):
    """Retry once on HTTP/2 connection drops (server closes idle connections)."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except httpx.RemoteProtocolError:
            if attempt >= retries:
                raise


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token()
        if not token:
            return jsonify({"error": "Token não fornecido"}), 401

        user = _validate_token(token)
        if not user:
            return jsonify({"error": "Token inválido ou expirado"}), 401

        profile = _get_profile(user.id)
        if not profile:
            return jsonify({"error": "Perfil não encontrado"}), 401

        # Usuário desativado perde acesso a tudo, mesmo com token ainda válido.
        if not profile.get("ativo", True):
            return jsonify({"error": "Conta desativada. Procure o administrador."}), 403

        g.user_id = user.id
        g.user_tipo = profile["tipo"]
        # Guarda o JWT da requisição para handlers que precisam consultar o
        # banco sob a identidade do usuário (RLS) via get_user_client().
        g.access_token = token
        return f(*args, **kwargs)

    return decorated


def require_role(*roles):
    """Uso: @require_role('admin', 'recepcionista')"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if g.user_tipo not in roles:
                return jsonify({"error": "Acesso negado"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def _get_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


def _validate_token(token):
    def _call():
        response = supabase.auth.get_user(token)
        return response.user

    try:
        return _with_retry(_call)
    except (AuthApiError, httpx.RemoteProtocolError):
        return None


def _get_profile(user_id):
    # select("*") em vez de colunas nomeadas para tolerar a coluna `ativo`
    # ainda não migrada: sem ela, `.get("ativo", True)` trata como ativo e o
    # app não quebra antes de rodar a migration 007.
    #
    # maybe_single() em vez de single(): retorna None quando não encontra registro
    # em vez de lançar PGRST116. Garante 401 limpo para usuários sem profile
    # (ex.: criados manualmente no Supabase sem passar pelo trigger).
    def _query():
        result = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    try:
        return _with_retry(_query)
    except Exception:
        return None

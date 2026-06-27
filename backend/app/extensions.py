from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def rate_limit_key() -> str:
    """Chave de contagem do rate limit.

    Usa o token do usuário autenticado (um balde por sessão) quando presente;
    caso contrário, cai no IP de origem — é o caso de endpoints públicos como
    o /auth/login, onde ainda não há token.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth
    return get_remote_address()


# Instância única importada pelos blueprints (para @limiter.limit em rotas
# específicas). Os limites e o storage são configurados em create_app via
# app.config (chaves RATELIMIT_*).
limiter = Limiter(key_func=rate_limit_key)

import os
from dotenv import load_dotenv

load_dotenv()


def _csv(value: str | None) -> list[str]:
    """Converte 'a, b ,c' em ['a', 'b', 'c'], descartando vazios."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    # ── Supabase ────────────────────────────────────────────────────────────
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    # ANON KEY: chave pública, usada em clientes por requisição (login e
    # operações sob RLS com o JWT do usuário).
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    # SERVICE ROLE KEY: chave SECRETA, bypassa RLS. NUNCA deve ir para o
    # frontend nem para logs/respostas. Só existe no ambiente do backend.
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

    # ── CORS ────────────────────────────────────────────────────────────────
    # Lista explícita de origens permitidas (sem wildcard). Em produção,
    # defina ALLOWED_ORIGINS com a(s) URL(s) do Next.js, ex.:
    # ALLOWED_ORIGINS="https://app.minhaacademia.com,https://homolog.minhaacademia.com"
    # No dev, o Next.js pode ser aberto tanto via "localhost" quanto via
    # "127.0.0.1" — para o navegador são origens distintas, então liberamos
    # ambas. Em produção, defina ALLOWED_ORIGINS explicitamente.
    ALLOWED_ORIGINS = _csv(os.getenv("ALLOWED_ORIGINS")) or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ── Rate limiting (Flask-Limiter) ───────────────────────────────────────
    # Em produção use um backend compartilhado (ex.: redis://...) para que o
    # limite valha entre múltiplos workers/instâncias. "memory://" só serve
    # para dev/single-process.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per minute")
    RATELIMIT_LOGIN = os.getenv("RATELIMIT_LOGIN", "10 per minute;50 per hour")

    # ── E-mail ──────────────────────────────────────────────────────────────
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_FROM = os.getenv("EMAIL_FROM")

    # Variáveis sem as quais o backend não deve subir.
    _REQUIRED = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")

    @classmethod
    def missing_required(cls) -> list[str]:
        return [name for name in cls._REQUIRED if not getattr(cls, name)]

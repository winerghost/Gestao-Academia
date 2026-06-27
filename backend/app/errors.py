"""Helpers para tratar erros de forma segura (sem vazar detalhes internos)."""


def email_ja_cadastrado(exc: Exception) -> bool:
    """Heurística para identificar 'e-mail já existe' vindo do Supabase Auth.

    Permite devolver uma mensagem amigável e específica para esse caso comum,
    sem expor o texto cru da exceção (que pode conter detalhes internos).
    """
    texto = str(exc).lower()
    marcadores = ("already registered", "already been registered",
                  "email_exists", "user already", "duplicate")
    return any(m in texto for m in marcadores)

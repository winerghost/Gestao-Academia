"""Helpers para tratar erros de forma segura (sem vazar detalhes internos)."""
from flask import jsonify


def erro_campo(campo: str, mensagem: str, status: int = 400):
    """Retorna erro estruturado com a chave `fields`, indicando qual campo falhou.

    Exemplo:
        if email_ja_cadastrado(exc):
            return erro_campo("email", "E-mail já cadastrado.", 409)
    """
    return jsonify({"error": mensagem, "fields": {campo: mensagem}}), status


def email_ja_cadastrado(exc: Exception) -> bool:
    """Heurística para identificar 'e-mail já existe' vindo do Supabase Auth.

    Permite devolver uma mensagem amigável e específica para esse caso comum,
    sem expor o texto cru da exceção (que pode conter detalhes internos).
    """
    texto = str(exc).lower()
    marcadores = ("already registered", "already been registered",
                  "email_exists", "user already", "duplicate")
    return any(m in texto for m in marcadores)


def violacao_unicidade(exc: Exception) -> bool:
    """Identifica violação de UNIQUE/constraint duplicada vinda do Postgres/PostgREST.

    Serve de rede de segurança quando uma constraint de banco (ex.: índice
    único parcial de vínculo ativo) barra a operação mesmo após a checagem
    da aplicação — caso de corrida entre duas requisições concorrentes.
    O Postgres usa o SQLSTATE 23505 para 'unique_violation'.
    """
    code = getattr(exc, "code", None)
    if code == "23505":
        return True
    texto = str(exc).lower()
    marcadores = ("23505", "duplicate key", "unique constraint",
                  "already exists", "uq_aluno_planos_ativo", "uq_mensalidades_ap_vcto")
    return any(m in texto for m in marcadores)

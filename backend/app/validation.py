"""Decorator de validação de corpo de requisição com Pydantic.

Inclui também validadores leves para *query params* (mês e datas), usados nas
listagens/relatórios: um valor malformado vindo da URL não pode chegar ao
PostgREST e virar um 500 (que ainda vazaria detalhes do banco).
"""
import re
from datetime import date
from functools import wraps

from flask import jsonify, request
from pydantic import BaseModel, ValidationError

# "AAAA-MM" com mês entre 01 e 12.
_ANO_MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def mes_valido(mes: str | None) -> bool:
    """True se `mes` está no formato AAAA-MM (ex.: '2026-06')."""
    return bool(mes) and bool(_ANO_MES_RE.match(mes))


def data_iso_valida(valor: str | None) -> bool:
    """True se `valor` é uma data ISO válida (AAAA-MM-DD)."""
    if not valor:
        return False
    try:
        date.fromisoformat(valor)
        return True
    except (ValueError, TypeError):
        return False


def _formatar_erros(exc: ValidationError) -> dict:
    """Converte os erros do Pydantic em {campo: mensagem} legível."""
    out: dict[str, str] = {}
    for err in exc.errors():
        campo = ".".join(str(p) for p in err["loc"]) or "_body"
        out[campo] = err["msg"]
    return out


def validate_body(model: type[BaseModel]):
    """Valida o corpo JSON contra `model` e injeta o resultado como `payload`.

    - 400 se o corpo não for um objeto JSON válido.
    - 422 com os campos inválidos se a validação falhar.
    Deve ficar abaixo dos decorators de auth (`@require_role`/`@require_auth`),
    para não validar entrada de quem nem está autenticado/autorizado.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            raw = request.get_json(silent=True)
            if not isinstance(raw, dict):
                return jsonify({"error": "Corpo JSON inválido ou ausente"}), 400
            try:
                payload = model.model_validate(raw)
            except ValidationError as exc:
                return jsonify({
                    "error": "Dados inválidos",
                    "fields": _formatar_erros(exc),
                }), 422
            kwargs["payload"] = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator

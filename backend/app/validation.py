"""Decorator de validação de corpo de requisição com Pydantic."""
from functools import wraps

from flask import jsonify, request
from pydantic import BaseModel, ValidationError


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

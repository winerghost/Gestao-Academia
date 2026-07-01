"""Testes unitários para _mensagem_pydantic_sanitizada (sem precisar rodar rotas)."""
import pytest
from app.validation import _mensagem_pydantic_sanitizada


class TestMensagemPydanticSanitizada:
    """Valida que tipos de erro do Pydantic são traduzidos para mensagens PT-BR seguras."""

    def test_missing(self):
        """Campo obrigatório."""
        err = {"type": "missing", "loc": ("email",)}
        assert _mensagem_pydantic_sanitizada(err) == "Campo obrigatório."

    def test_string_too_short(self):
        """Mínimo de N caracteres."""
        err = {"type": "string_too_short", "ctx": {"min_length": 8}}
        assert _mensagem_pydantic_sanitizada(err) == "Mínimo de 8 caracteres."

    def test_string_too_short_sem_ctx(self):
        """Fallback quando ctx vazio."""
        err = {"type": "string_too_short", "ctx": {}}
        assert _mensagem_pydantic_sanitizada(err) == "Mínimo de ? caracteres."

    def test_string_too_long(self):
        """Máximo de N caracteres."""
        err = {"type": "string_too_long", "ctx": {"max_length": 120}}
        assert _mensagem_pydantic_sanitizada(err) == "Máximo de 120 caracteres."

    def test_string_pattern_mismatch(self):
        """Formato inválido (nunca expõe o regex)."""
        err = {"type": "string_pattern_mismatch", "ctx": {"pattern": r"^[^@\s]+@"}}
        assert _mensagem_pydantic_sanitizada(err) == "Formato inválido."

    def test_literal_error(self):
        """Valor inválido para este campo (ex: status 'ativo'/'inativo')."""
        err = {"type": "literal_error", "ctx": {"expected": "'ativo', 'inativo'"}}
        assert _mensagem_pydantic_sanitizada(err) == "Valor inválido para este campo."

    def test_extra_forbidden(self):
        """Campo não permitido (mass-assignment)."""
        err = {"type": "extra_forbidden", "ctx": {"extra": "campo_nao_esperado"}}
        assert _mensagem_pydantic_sanitizada(err) == "Campo não permitido."

    def test_less_than_equal(self):
        """Valor fora do intervalo permitido."""
        err = {"type": "less_than_equal", "ctx": {"le": 30}}
        assert _mensagem_pydantic_sanitizada(err) == "Valor fora do intervalo permitido."

    def test_greater_than(self):
        """Valor fora do intervalo permitido (capturado por 'in' antes)."""
        # Nota: `greater_than` nunca chega aqui isolado porque está em "in"
        # acima, mas testamos por completude e futuro-proofing.
        err = {"type": "greater_than", "ctx": {"gt": 0}}
        assert _mensagem_pydantic_sanitizada(err) == "Valor fora do intervalo permitido."

    def test_less_than(self):
        """Valor muito grande."""
        err = {"type": "less_than", "ctx": {"lt": 100}}
        assert _mensagem_pydantic_sanitizada(err) == "Valor muito grande."

    def test_value_error_com_mensagem_pt(self):
        """Mantém mensagem customizada em PT-BR (ex: do @field_validator)."""
        err = {"type": "value_error", "msg": "CPF deve conter 11 dígitos"}
        assert _mensagem_pydantic_sanitizada(err) == "CPF deve conter 11 dígitos"

    def test_value_error_com_palavra_deve(self):
        """Detecta 'deve' na mensagem."""
        err = {"type": "value_error", "msg": "Foto deve ter menos de 5MB"}
        assert _mensagem_pydantic_sanitizada(err) == "Foto deve ter menos de 5MB"

    def test_value_error_em_ingles(self):
        """Fallback para mensagem genérica se msg cru vem em inglês."""
        err = {"type": "value_error", "msg": "value must be positive"}
        assert _mensagem_pydantic_sanitizada(err) == "Valor inválido."

    def test_tipo_desconhecido(self):
        """Tipo não mapeado → fallback."""
        err = {"type": "unknown_error_type"}
        assert _mensagem_pydantic_sanitizada(err) == "Valor inválido."

    def test_sem_type(self):
        """Type não fornecido → default 'value_error'."""
        err = {"msg": "some message"}
        assert _mensagem_pydantic_sanitizada(err) == "Valor inválido."

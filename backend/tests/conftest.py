"""Fixtures compartilhadas por toda a suíte (auto-descobertas pelo pytest).

Antes, cada arquivo repetia a mesma fixture `client`. Centralizar aqui remove a
duplicação e garante que todos os testes montem o app do mesmo jeito (TESTING=True,
sem scheduler/rate-limit — ver create_app).
"""
import pytest

from app import create_app


@pytest.fixture
def client():
    """App Flask em modo teste + test_client isolado por teste."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

from unittest.mock import patch, MagicMock
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth_headers():
    return {"Authorization": "Bearer token-fake"}


def _mock_auth(mock_supa, tipo="admin"):
    user = MagicMock()
    user.id = "user-uuid"
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    perfil = MagicMock(data={"tipo": tipo})
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = perfil
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = perfil


def test_criar_plano_campos_obrigatorios(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/planos", json={"nome": "Musculação"}, headers=_auth_headers())
        assert res.status_code == 422
        assert "valor" in res.get_json()["fields"]


def test_criar_plano_valor_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/planos", json={
            "nome": "Musculação", "valor": -50, "duracao_dias": 30
        }, headers=_auth_headers())
        assert res.status_code == 422
        assert "valor" in res.get_json()["fields"]


def test_criar_plano_sucesso(client):
    with patch("app.planos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "plano-uuid", "nome": "Musculação", "valor": 99.90, "duracao_dias": 30}]
        )

        res = client.post("/planos", json={
            "nome": "Musculação", "valor": 99.90, "duracao_dias": 30
        }, headers=_auth_headers())
        assert res.status_code == 201
        assert res.get_json()["nome"] == "Musculação"


def test_criar_plano_acesso_negado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.post("/planos", json={
            "nome": "Natação", "valor": 120, "duracao_dias": 30
        }, headers=_auth_headers())
        assert res.status_code == 403

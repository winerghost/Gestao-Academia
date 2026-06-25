from unittest.mock import patch, MagicMock
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_login_sem_dados(client):
    res = client.post("/auth/login", json={})
    assert res.status_code == 400
    assert "obrigatórios" in res.get_json()["error"]


def test_login_credenciais_invalidas(client):
    with patch("app.auth.routes.supabase") as mock_supa:
        from gotrue.errors import AuthApiError
        mock_supa.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials", 400, {}
        )
        res = client.post("/auth/login", json={"email": "x@x.com", "password": "errada"})
        assert res.status_code == 401


def test_rota_protegida_sem_token(client):
    res = client.get("/auth/me")
    assert res.status_code == 401
    assert "Token" in res.get_json()["error"]


def test_login_sucesso(client):
    with patch("app.auth.routes.supabase") as mock_supa:
        session = MagicMock()
        session.session.access_token = "token-fake"
        session.user.id = "uuid-fake"
        session.user.email = "admin@academia.com"
        mock_supa.auth.sign_in_with_password.return_value = session

        res = client.post(
            "/auth/login",
            json={"email": "admin@academia.com", "password": "senha123"},
        )
        assert res.status_code == 200
        assert res.get_json()["access_token"] == "token-fake"

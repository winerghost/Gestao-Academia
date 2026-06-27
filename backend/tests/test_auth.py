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
    assert res.status_code == 422
    fields = res.get_json()["fields"]
    assert "email" in fields and "password" in fields


def test_login_credenciais_invalidas(client):
    with patch("app.auth.routes.get_anon_client") as mock_factory:
        from gotrue.errors import AuthApiError
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials", 400, {}
        )
        mock_factory.return_value = mock_client
        res = client.post("/auth/login", json={"email": "x@x.com", "password": "errada"})
        assert res.status_code == 401


def test_rota_protegida_sem_token(client):
    res = client.get("/auth/me")
    assert res.status_code == 401
    assert "Token" in res.get_json()["error"]


def test_login_rate_limit():
    """Após exceder o limite, o login responde 429 (mitiga brute force)."""
    from app.extensions import limiter
    from app.config import Config
    from gotrue.errors import AuthApiError

    app = create_app()
    app.config["TESTING"] = True
    original = Config.RATELIMIT_LOGIN
    Config.RATELIMIT_LOGIN = "2 per minute"
    # Reabilita o limiter para este app (em testes ele nasce desligado).
    app.config["RATELIMIT_ENABLED"] = True
    limiter.init_app(app)
    limiter.enabled = True
    try:
        with app.test_client() as c, \
             patch("app.auth.routes.get_anon_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.auth.sign_in_with_password.side_effect = AuthApiError(
                "Invalid login credentials", 400, {}
            )
            mock_factory.return_value = mock_client
            codes = [
                c.post("/auth/login", json={"email": "a@a.com", "password": "x"}).status_code
                for _ in range(3)
            ]
        assert codes[0] == 401      # dentro do limite, credenciais inválidas
        assert codes[-1] == 429     # estourou o limite
    finally:
        Config.RATELIMIT_LOGIN = original
        limiter.enabled = False


def test_login_sucesso(client):
    with patch("app.auth.routes.get_anon_client") as mock_factory, \
         patch("app.auth.routes.supabase") as mock_supa:
        session = MagicMock()
        session.session.access_token = "token-fake"
        session.session.refresh_token = "refresh-fake"
        session.user.id = "uuid-fake"
        session.user.email = "admin@academia.com"
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = session
        mock_factory.return_value = mock_client
        # Login agora confere se a conta está ativa antes de liberar o token.
        mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"ativo": True}
        )

        res = client.post(
            "/auth/login",
            json={"email": "admin@academia.com", "password": "senha123"},
        )
        assert res.status_code == 200
        assert res.get_json()["access_token"] == "token-fake"
        assert res.get_json()["refresh_token"] == "refresh-fake"

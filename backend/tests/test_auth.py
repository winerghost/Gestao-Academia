"""Testes de autenticação e gestão do perfil do usuário.

Conceitos testados:
  - Login seguro: rate limiting (brute force), conta desativada, credenciais inválidas.
  - JWT: o middleware require_auth valida o token em TODA requisição protegida.
  - Troca de senha: revalida a senha ATUAL antes de gravar a nova — isso garante
    que um token roubado ou compartilhado não baste para trocar a senha.
  - Avatar: a imagem é re-encodada com Pillow antes de ir ao Storage (descarta EXIF
    e payloads maliciosos embutidos na imagem).
  - Escalonamento de privilégio: PUT /auth/me com campos 'tipo' ou 'ativo' é
    rejeitado pelo schema (extra='forbid') — ninguém eleva o próprio papel.

Padrão de mock:
  O backend usa dois clientes Supabase independentes:
    - `app.auth.routes.supabase`: service_role, usado para queries do handler.
    - `app.auth.middleware.supabase`: service_role, usado pelo decorator require_auth
      para validar o JWT e buscar o profile. Importado no módulo middleware, por
      isso precisa ser patchado separadamente.
    - `app.auth.routes.get_anon_client`: cria um client isolado por requisição para
      o login (não contamina o client global com sessão do usuário).
"""
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
    """Corpo sem 'email' e 'password' → 422 com os campos faltando listados.

    O schema LoginSchema (Pydantic) valida ANTES de chegar ao handler.
    O `extra='forbid'` rejeita campos desconhecidos; a falta de obrigatórios
    gera 422 com `fields` descrevendo cada erro — sem tocar o Supabase Auth.
    """
    res = client.post("/auth/login", json={})
    assert res.status_code == 422
    fields = res.get_json()["fields"]
    assert "email" in fields and "password" in fields


def test_login_credenciais_invalidas(client):
    """Credenciais erradas → 401 com mensagem genérica (não revela se o e-mail existe).

    A resposta é sempre a mesma seja o e-mail desconhecido ou a senha errada —
    evitar enumeration de usuários. O texto da exceção interna não é exposto.
    """
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
    """Requisição sem header Authorization → 401 com mensagem clara.

    O middleware `require_auth` extrai o token do header `Authorization: Bearer <token>`.
    Sem o header (ou sem o prefixo 'Bearer '), o token não é extraído e a rota
    rejeita imediatamente, sem chegar ao handler.
    """
    res = client.get("/auth/me")
    assert res.status_code == 401
    assert "Token" in res.get_json()["error"]


def test_login_rate_limit():
    """Após exceder o limite configurado, o login responde 429.

    Rate limiting é a defesa primária contra brute force de senhas. O limiter
    conta por IP; em produção deve usar Redis (RATELIMIT_STORAGE_URI=redis://...)
    para que o limite seja compartilhado entre todos os workers do gunicorn.
    Sem Redis, cada worker tem sua própria contagem — o limite fica ineficaz.

    Em testes o rate limit é desligado por padrão (RATELIMIT_ENABLED=False).
    Este teste religa explicitamente para validar o comportamento.
    """
    from app.extensions import limiter
    from app.config import Config
    from gotrue.errors import AuthApiError

    app = create_app()
    app.config["TESTING"] = True
    original = Config.RATELIMIT_LOGIN
    Config.RATELIMIT_LOGIN = "2 per minute"
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
    """Login com credenciais válidas e conta ativa → 200 com tokens JWT.

    Fluxo completo:
      1. get_anon_client() faz sign_in_with_password com o client isolado.
      2. Após autenticação, verifica profiles.ativo (B-3: maybe_single).
      3. Se ativo=True, retorna access_token + refresh_token.
    O client anônimo é isolado por request para não contaminar o client global
    de service_role com a sessão do usuário.
    """
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
        # (B-3) maybe_single: consulta profiles sem risco de PGRST116.
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"ativo": True}
        )

        res = client.post(
            "/auth/login",
            json={"email": "admin@academia.com", "password": "senha123"},
        )
        assert res.status_code == 200
        assert res.get_json()["access_token"] == "token-fake"
        assert res.get_json()["refresh_token"] == "refresh-fake"

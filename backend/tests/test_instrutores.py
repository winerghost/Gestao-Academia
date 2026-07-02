"""Testes para rota de instrutores (POST/GET)."""
from unittest.mock import patch, MagicMock

from tests._helpers import mock_auth, auth_headers as _auth_headers

_UID_SELF = "00000000-0000-0000-0000-000000000001"
_UID_OTHER = "00000000-0000-0000-0000-000000000099"


def _mock_auth(mock_supa, user_id=_UID_SELF, tipo="admin"):
    """Delega ao helper canônico; user_id default = _UID_SELF (self-guards)."""
    return mock_auth(mock_supa, tipo=tipo, user_id=user_id)


# ── POST /instrutores ─────────────────────────────────────────────────────────


def test_criar_instrutor_sucesso(client):
    """Admin cria instrutor → 201."""
    with patch("app.instrutores.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        # Simula sucesso do auth.admin.create_user
        mock_supa.auth.admin.create_user.return_value = MagicMock(
            user=MagicMock(id="new-instrutor-id")
        )
        # Simula sucesso do insert em instrutores
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new-instrutor-id", "nome": "João Instrutor"}]
        )

        res = client.post("/instrutores", json={
            "nome": "João Instrutor",
            "email": "joao@academia.com",
            "senha": "Senha@1234",
            "especialidade": "Musculação",
        }, headers=_auth_headers())

        assert res.status_code == 201
        body = res.get_json()
        assert body["id"] == "new-instrutor-id"
        assert body["nome"] == "João Instrutor"


def test_criar_instrutor_email_duplicado_retorna_400_com_field(client):
    """E-mail já cadastrado → 400 com campo 'email' em 'fields'.

    Simula falha do auth.admin.create_user (usuário já existe).
    Deve retornar 400 e indicar qual campo falhou.
    """
    with patch("app.instrutores.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        # Simula exceção de e-mail já registrado
        mock_supa.auth.admin.create_user.side_effect = Exception(
            "AuthApiError: User already registered"
        )

        res = client.post("/instrutores", json={
            "nome": "Novo Instrutor",
            "email": "ja@existe.com",
            "senha": "Senha@1234",
        }, headers=_auth_headers())

        assert res.status_code == 400
        body = res.get_json()
        assert body["error"] == "E-mail já cadastrado."
        assert body["fields"]["email"] == "E-mail já cadastrado."
        assert "detail" not in body


def test_criar_instrutor_nao_admin_bloqueado(client):
    """Recepcionista não pode criar instrutor → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")

        res = client.post("/instrutores", json={
            "nome": "João",
            "email": "joao@academia.com",
            "senha": "Senha@1234",
        }, headers=_auth_headers())

        assert res.status_code == 403


# ── GET /instrutores ──────────────────────────────────────────────────────────
# (listagem coberta implicitamente pelos outros testes; foco em error handling)

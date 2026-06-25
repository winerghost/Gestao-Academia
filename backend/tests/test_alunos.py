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
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"tipo": tipo}
    )


# ── Listar alunos ─────────────────────────────────────────────────────────────

def test_listar_alunos_sem_token(client):
    res = client.get("/alunos")
    assert res.status_code == 401


def test_listar_alunos_como_admin(client):
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        chain = MagicMock()
        chain.order.return_value.execute.return_value = MagicMock(data=[
            {"id": "uuid-1", "cpf": "12345678901", "status": "ativo"}
        ])
        mock_supa.table.return_value.select.return_value.order = chain.order

        res = client.get("/alunos", headers=_auth_headers())
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)


# ── Criar aluno ───────────────────────────────────────────────────────────────

def test_criar_aluno_campos_obrigatorios(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/alunos", json={"nome": "João"}, headers=_auth_headers())
        assert res.status_code == 400
        assert "obrigatório" in res.get_json()["error"]


def test_criar_aluno_cpf_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/alunos", json={
            "nome": "João", "email": "j@j.com", "senha": "123", "cpf": "123"
        }, headers=_auth_headers())
        assert res.status_code == 400
        assert "CPF" in res.get_json()["error"]


def test_criar_aluno_sucesso(client):
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        user = MagicMock()
        user.id = "novo-uuid"
        mock_supa.auth.admin.create_user.return_value = MagicMock(user=user)
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "novo-uuid", "cpf": "12345678901", "status": "ativo"}]
        )

        res = client.post("/alunos", json={
            "nome": "João Silva",
            "email": "joao@academia.com",
            "senha": "Senha@123",
            "cpf": "123.456.789-01",
        }, headers=_auth_headers())
        assert res.status_code == 201


# ── Status ────────────────────────────────────────────────────────────────────

def test_status_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.patch(
            "/alunos/00000000-0000-0000-0000-000000000001/status",
            json={"status": "bloqueado"},
            headers=_auth_headers(),
        )
        assert res.status_code == 400

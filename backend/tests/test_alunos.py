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
        assert res.status_code == 422
        # email, senha e cpf faltando
        assert {"email", "senha", "cpf"} <= set(res.get_json()["fields"])


def test_criar_aluno_cpf_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/alunos", json={
            "nome": "João", "email": "j@j.com", "senha": "Senha@123", "cpf": "123"
        }, headers=_auth_headers())
        assert res.status_code == 422
        assert "cpf" in res.get_json()["fields"]


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


def test_criar_aluno_email_duplicado_nao_vaza_detalhe(client):
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.auth.admin.create_user.side_effect = Exception(
            "AuthApiError: User already registered"
        )

        res = client.post("/alunos", json={
            "nome": "João Silva",
            "email": "existe@academia.com",
            "senha": "Senha@123",
            "cpf": "123.456.789-01",
        }, headers=_auth_headers())

        assert res.status_code == 400
        body = res.get_json()
        assert body["error"] == "E-mail já cadastrado"
        assert "detail" not in body   # não expõe o texto cru da exceção


# ── Buscar por id (BOLA/IDOR via RLS) ─────────────────────────────────────────

def test_buscar_aluno_usa_client_rls(client):
    """GET /alunos/<id> consulta sob a identidade do usuário (RLS), e não
    com a service_role — é o que impede um usuário de ler aluno alheio."""
    with patch("app.alunos.routes.get_user_client") as mock_uc, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-uuid", "cpf": "12345678901"}
        )
        mock_uc.return_value = db

        res = client.get(
            "/alunos/00000000-0000-0000-0000-000000000001",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        mock_uc.assert_called_once()  # provou o uso do client sob RLS


def test_buscar_aluno_rls_nega_retorna_404(client):
    """Quando a RLS não devolve linha (aluno alheio), responde 404."""
    with patch("app.alunos.routes.get_user_client") as mock_uc, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_uc.return_value = db

        res = client.get(
            "/alunos/00000000-0000-0000-0000-000000000002",
            headers=_auth_headers(),
        )
        assert res.status_code == 404


# ── Telefone no cadastro ──────────────────────────────────────────────────────

def test_criar_aluno_com_telefone_atualiza_profile(client):
    """Quando telefone é enviado, deve atualizar profiles após criar o usuário."""
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        user = MagicMock()
        user.id = "novo-uuid"
        mock_supa.auth.admin.create_user.return_value = MagicMock(user=user)

        update_chain = MagicMock()
        update_chain.eq.return_value.execute.return_value = MagicMock(data=[{}])

        insert_chain = MagicMock()
        insert_chain.execute.return_value = MagicMock(
            data=[{"id": "novo-uuid", "cpf": "12345678901", "status": "ativo"}]
        )

        def table_router(name):
            m = MagicMock()
            if name == "profiles":
                m.update.return_value = update_chain
            else:
                m.insert.return_value = insert_chain
            return m

        mock_supa.table.side_effect = table_router

        res = client.post("/alunos", json={
            "nome": "João Silva",
            "email": "joao@academia.com",
            "senha": "Senha@123",
            "cpf": "123.456.789-01",
            "telefone": "(11) 99999-9999",
        }, headers=_auth_headers())

        assert res.status_code == 201
        # garante que profiles.update foi chamado com o telefone
        update_chain.eq.assert_called_once_with("id", "novo-uuid")


def test_criar_aluno_sem_telefone_nao_chama_profiles_update(client):
    """Sem telefone no payload, profiles.update não deve ser chamado."""
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
        # profiles.update jamais deve ter sido chamado
        for call_args in mock_supa.table.call_args_list:
            assert call_args[0][0] != "profiles"


def test_atualizar_aluno_telefone_vai_para_profiles(client):
    """PUT /alunos/<id> com telefone deve atualizar profiles, não alunos."""
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        profile_update = MagicMock()
        profile_update.eq.return_value.execute.return_value = MagicMock(data=[{}])

        aluno_select = MagicMock()
        aluno_select.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"profile_id": "profile-uuid"}
        )

        aluno_update = MagicMock()
        aluno_update.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "aluno-uuid", "cpf": "12345678901"}]
        )

        def table_router(name):
            m = MagicMock()
            if name == "profiles":
                m.update.return_value = profile_update
            else:
                m.select.return_value = aluno_select
                m.update.return_value = aluno_update
            return m

        mock_supa.table.side_effect = table_router

        res = client.put(
            "/alunos/00000000-0000-0000-0000-000000000001",
            json={"telefone": "(11) 88888-8888", "endereco": "Rua Nova, 10"},
            headers=_auth_headers(),
        )

        assert res.status_code == 200
        # profiles.update chamado com telefone
        profile_update.eq.assert_called_once_with("id", "profile-uuid")


# ── Status ────────────────────────────────────────────────────────────────────

def test_status_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.patch(
            "/alunos/00000000-0000-0000-0000-000000000001/status",
            json={"status": "bloqueado"},
            headers=_auth_headers(),
        )
        assert res.status_code == 422

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


def _mock_auth(mock_supa):
    user = MagicMock()
    user.id = "user-uuid"
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    perfil = MagicMock(data={"tipo": "aluno"})
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = perfil
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = perfil


# ── /portal/me ────────────────────────────────────────────────────────────────

def test_portal_me_sem_token(client):
    res = client.get("/portal/me")
    assert res.status_code == 401


def test_portal_me_retorna_dados_do_aluno(client):
    with patch("app.portal.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        aluno_mock = MagicMock()
        profile_mock = MagicMock()
        planos_mock = MagicMock()

        aluno_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-1", "status": "ativo", "frequencia_habilitada": True}
        )
        profile_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"nome": "João Silva", "telefone": "11999999999"}
        )
        planos_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"planos": {"nome": "Musculação"}}]
        )

        def table_mock(name):
            if name == "alunos":
                return aluno_mock
            if name == "profiles":
                return profile_mock
            if name == "aluno_planos":
                return planos_mock
            return MagicMock()

        mock_supa.table.side_effect = table_mock

        res = client.get("/portal/me", headers=_auth_headers())

    assert res.status_code == 200
    data = res.get_json()
    assert data["nome"] == "João Silva"
    assert data["status"] == "ativo"
    assert data["frequencia_habilitada"] is True
    assert "Musculação" in data["planos"]


def test_portal_me_aluno_nao_encontrado(client):
    with patch("app.portal.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        aluno_mock = MagicMock()
        aluno_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_supa.table.return_value = aluno_mock

        res = client.get("/portal/me", headers=_auth_headers())

    assert res.status_code == 404


# ── /portal/mensalidades ──────────────────────────────────────────────────────

def test_portal_mensalidades_sem_token(client):
    res = client.get("/portal/mensalidades")
    assert res.status_code == 401


def test_portal_mensalidades_retorna_lista(client):
    with patch("app.portal.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        aluno_mock = MagicMock()
        ap_mock = MagicMock()
        mens_mock = MagicMock()

        aluno_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-1", "status": "ativo", "frequencia_habilitada": False}
        )
        ap_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "ap-1"}]
        )
        mens_mock.select.return_value.in_.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "mens-1",
                "valor": 100.0,
                "juros": 0.0,
                "valor_total": 100.0,
                "data_vencimento": "2026-07-01",
                "data_pagamento": None,
                "status": "pendente",
                "aluno_planos": {"planos": {"nome": "Musculação"}},
            }]
        )

        def table_mock(name):
            if name == "alunos":
                return aluno_mock
            if name == "aluno_planos":
                return ap_mock
            if name == "mensalidades":
                return mens_mock
            return MagicMock()

        mock_supa.table.side_effect = table_mock

        res = client.get("/portal/mensalidades", headers=_auth_headers())

    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["status"] == "pendente"
    assert data[0]["valor"] == 100.0


def test_portal_mensalidades_sem_aluno_retorna_vazio(client):
    with patch("app.portal.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        aluno_mock = MagicMock()
        aluno_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_supa.table.return_value = aluno_mock

        res = client.get("/portal/mensalidades", headers=_auth_headers())

    assert res.status_code == 200
    assert res.get_json() == []


# ── /portal/frequencias ───────────────────────────────────────────────────────

def test_portal_frequencias_sem_token(client):
    res = client.get("/portal/frequencias")
    assert res.status_code == 401


def test_portal_frequencias_habilitada_retorna_lista(client):
    with patch("app.portal.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        aluno_mock = MagicMock()
        freq_mock = MagicMock()

        aluno_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-1", "status": "ativo", "frequencia_habilitada": True}
        )
        freq_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "f-1", "data_hora": "2026-06-20T09:00:00"},
                {"id": "f-2", "data_hora": "2026-06-18T10:30:00"},
            ]
        )

        def table_mock(name):
            if name == "alunos":
                return aluno_mock
            if name == "frequencias":
                return freq_mock
            return MagicMock()

        mock_supa.table.side_effect = table_mock

        res = client.get("/portal/frequencias", headers=_auth_headers())

    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 2
    assert data[0]["id"] == "f-1"


def test_portal_frequencias_desabilitada_retorna_vazio(client):
    with patch("app.portal.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        aluno_mock = MagicMock()
        aluno_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-1", "status": "ativo", "frequencia_habilitada": False}
        )
        mock_supa.table.return_value = aluno_mock

        res = client.get("/portal/frequencias", headers=_auth_headers())

    assert res.status_code == 200
    assert res.get_json() == []

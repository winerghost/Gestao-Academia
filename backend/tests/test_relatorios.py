from unittest.mock import patch, MagicMock

from tests._helpers import mock_auth as _mock_auth, auth_headers as _auth_headers


def _aluno_fake():
    return {
        "cpf": "12345678901",
        "status": "ativo",
        "created_at": "2026-01-15T10:00:00",
        "profiles": {"nome": "João Silva", "telefone": "11999999999"},
        "aluno_planos": [{"planos": {"nome": "Musculação"}}],
    }


def _mensalidade_fake():
    return {
        "valor": 100.0,
        "juros": 0.0,
        "valor_total": 100.0,
        "data_vencimento": "2026-06-01",
        "data_pagamento": "2026-06-01",
        "status": "paga",
        "aluno_planos": {
            "planos": {"nome": "Musculação"},
            "alunos": {"profiles": {"nome": "João Silva"}},
        },
    }


# ── Validação de formato ──────────────────────────────────────────────────────

def test_formato_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.get("/relatorios/alunos?formato=word", headers=_auth_headers())
        assert res.status_code == 400
        assert "formato" in res.get_json()["error"]


def test_sem_token_retorna_401(client):
    res = client.get("/relatorios/alunos")
    assert res.status_code == 401


# ── Relatório de alunos ───────────────────────────────────────────────────────

def test_relatorio_alunos_pdf(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[_aluno_fake()]
        )

        res = client.get("/relatorios/alunos?formato=pdf", headers=_auth_headers())
        assert res.status_code == 200
        assert res.content_type == "application/pdf"
        assert res.headers["Content-Disposition"].endswith(".pdf")


def test_relatorio_alunos_excel(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[_aluno_fake()]
        )

        res = client.get("/relatorios/alunos?formato=excel", headers=_auth_headers())
        assert res.status_code == 200
        assert "spreadsheetml" in res.content_type
        assert res.headers["Content-Disposition"].endswith(".xlsx")


# ── Relatório financeiro ──────────────────────────────────────────────────────

def test_relatorio_financeiro_pdf(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[_mensalidade_fake()]
        )

        res = client.get("/relatorios/financeiro?formato=pdf&mes=2026-06", headers=_auth_headers())
        assert res.status_code == 200
        assert res.content_type == "application/pdf"


# ── Relatório de inadimplência ────────────────────────────────────────────────

def test_relatorio_inadimplencia_excel(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{
                "valor": 100.0,
                "data_vencimento": "2026-05-01",
                "aluno_planos": {
                    "planos": {"nome": "Natação"},
                    "alunos": {
                        "cpf": "12345678901",
                        "profiles": {"nome": "Maria", "telefone": "11988887777"},
                    },
                },
            }]
        )

        res = client.get("/relatorios/inadimplencia?formato=excel", headers=_auth_headers())
        assert res.status_code == 200
        assert "spreadsheetml" in res.content_type


def test_relatorio_inadimplencia_vazio_pdf(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        res = client.get("/relatorios/inadimplencia?formato=pdf", headers=_auth_headers())
        assert res.status_code == 200
        assert res.content_type == "application/pdf"


# ── Permissões de Recepcionista ───────────────────────────────────────────────

def _config_perms(relatorio_financeiro=False, relatorio_inadimplencia=False):
    """Cria mock de academia_config com as permissões especificadas."""
    tbl = MagicMock()
    tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"permissoes_recepcionista": {
            "relatorio_financeiro": relatorio_financeiro,
            "relatorio_inadimplencia": relatorio_inadimplencia,
        }}
    )
    return tbl


def test_financeiro_recep_sem_permissao_retorna_403(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        mock_supa.table.side_effect = lambda name: _config_perms() if name == "academia_config" else MagicMock()

        res = client.get("/relatorios/financeiro?formato=pdf", headers=_auth_headers())
        assert res.status_code == 403
        assert "Recepcionista" in res.get_json()["error"]


def test_financeiro_recep_com_permissao_retorna_200(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")

        chain = mock_supa.table.return_value.select.return_value
        chain.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"permissoes_recepcionista": {"relatorio_financeiro": True, "relatorio_inadimplencia": False}}
        )
        chain.gte.return_value.lte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[_mensalidade_fake()]
        )

        res = client.get("/relatorios/financeiro?formato=pdf&mes=2026-06", headers=_auth_headers())
        assert res.status_code == 200
        assert res.content_type == "application/pdf"


def test_inadimplencia_recep_sem_permissao_retorna_403(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        mock_supa.table.side_effect = lambda name: _config_perms() if name == "academia_config" else MagicMock()

        res = client.get("/relatorios/inadimplencia?formato=pdf", headers=_auth_headers())
        assert res.status_code == 403


def test_inadimplencia_recep_com_permissao_retorna_200(client):
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")

        config_tbl = _config_perms(relatorio_inadimplencia=True)
        data_tbl = MagicMock()
        data_tbl.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[])

        mock_supa.table.side_effect = lambda name: config_tbl if name == "academia_config" else data_tbl

        res = client.get("/relatorios/inadimplencia?formato=pdf", headers=_auth_headers())
        assert res.status_code == 200


def test_alunos_recep_sem_permissao_especial_retorna_200(client):
    """Relatório de alunos não tem restrição por permissão — recepcionista sempre acessa."""
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        mock_supa.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[_aluno_fake()]
        )

        res = client.get("/relatorios/alunos?formato=pdf", headers=_auth_headers())
        assert res.status_code == 200


def test_financeiro_admin_sempre_retorna_200(client):
    """Admin acessa o relatório financeiro independente de qualquer config."""
    with patch("app.relatorios.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[_mensalidade_fake()]
        )

        res = client.get("/relatorios/financeiro?formato=pdf&mes=2026-06", headers=_auth_headers())
        assert res.status_code == 200

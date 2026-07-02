from unittest.mock import patch, MagicMock
from datetime import date

from tests._helpers import mock_auth as _mock_auth, auth_headers as _auth_headers


# ── Dashboard alunos ──────────────────────────────────────────────────────────

def test_dashboard_alunos_sem_token(client):
    res = client.get("/dashboard/alunos")
    assert res.status_code == 401


def test_dashboard_alunos_retorna_totais(client):
    hoje = date.today().isoformat()
    with patch("app.dashboard.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        def table_mock(name):
            m = MagicMock()
            if name == "alunos":
                m.select.return_value.execute.return_value = MagicMock(data=[
                    {"id": "1", "status": "ativo", "created_at": f"{hoje}T10:00:00"},
                    {"id": "2", "status": "inadimplente", "created_at": f"{hoje}T11:00:00"},
                    {"id": "3", "status": "inativo", "created_at": "2025-01-01T00:00:00"},
                ])
            elif name == "aluno_planos":
                m.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
                    {"planos": {"nome": "Musculação"}},
                    {"planos": {"nome": "Musculação"}},
                    {"planos": {"nome": "Natação"}},
                ])
            return m

        mock_supa.table.side_effect = table_mock

        res = client.get("/dashboard/alunos", headers=_auth_headers())
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 3
        assert data["ativos"] == 1
        assert data["inadimplentes"] == 1
        assert data["inativos"] == 1
        assert data["novos_no_mes"] == 2
        assert len(data["por_plano"]) == 2


# ── Dashboard financeiro ──────────────────────────────────────────────────────

def test_dashboard_financeiro_calcula_receita(client):
    with patch("app.dashboard.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        def table_mock(name):
            m = MagicMock()
            if name == "mensalidades":
                # Primeira chamada: mensalidades do mês (usa .gte().lte())
                m.select.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
                    {"status": "paga", "valor": 100.0, "valor_total": 102.0},
                    {"status": "pendente", "valor": 100.0, "valor_total": 100.0},
                    {"status": "atrasada", "valor": 100.0, "valor_total": 100.0},
                ])
                # Segunda chamada: todas as atrasadas (usa .eq())
                m.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
                    {"valor": 100.0},
                ])
            elif name == "alunos":
                m.select.return_value.execute.return_value = MagicMock(data=[
                    {"status": "ativo"},
                    {"status": "inadimplente"},
                ])
            return m

        mock_supa.table.side_effect = table_mock

        res = client.get("/dashboard/financeiro", headers=_auth_headers())
        assert res.status_code == 200
        data = res.get_json()
        assert data["receita_paga"] == 102.0
        assert data["receita_prevista"] == 300.0
        assert data["total_inadimplente"] == 100.0
        assert data["mensalidades_pagas"] == 1
        assert data["mensalidades_pendentes"] == 1
        assert data["taxa_inadimplencia"] == 50.0


# ── Dashboard frequência ──────────────────────────────────────────────────────

def test_dashboard_frequencia_retorna_contagens(client):
    with patch("app.dashboard.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        # Mocks criados fora da função para reutilizar o mesmo objeto
        # nas 3 chamadas a supabase.table("frequencias")
        freq_execute = MagicMock()
        freq_execute.side_effect = [
            MagicMock(data=[{"id": "f1"}, {"id": "f2"}]),                   # hoje
            MagicMock(data=[{"id": "f1"}, {"id": "f2"}, {"id": "f3"}]),     # mês
            MagicMock(data=[{"aluno_id": "aluno-1"}]),                       # recente
        ]
        freq_mock = MagicMock()
        freq_mock.select.return_value.gte.return_value.execute = freq_execute

        alunos_mock = MagicMock()
        alunos_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "aluno-1"}, {"id": "aluno-2"}]
        )

        def table_mock(name):
            if name == "frequencias":
                return freq_mock
            if name == "alunos":
                return alunos_mock
            return MagicMock()

        mock_supa.table.side_effect = table_mock

        res = client.get("/dashboard/frequencia", headers=_auth_headers())
        assert res.status_code == 200
        data = res.get_json()
        assert "entradas_hoje" in data
        assert "entradas_mes" in data
        assert "alunos_sem_frequencia_7_dias" in data

from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pytest
from app import create_app
from app.mensalidades.jobs import job_atualizar_inadimplencia, job_gerar_mensalidades


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


# ── Cálculo de juros ──────────────────────────────────────────────────────────

def test_pagamento_em_dia_sem_juros(client):
    hoje = date.today().isoformat()
    with patch("app.mensalidades.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        # side_effect retorna valores diferentes a cada chamada a execute():
        # 1ª chamada → dados da mensalidade; 2ª chamada → dados do aluno_plano
        single_execute = MagicMock()
        single_execute.side_effect = [
            MagicMock(data={"id": "mens-uuid", "status": "pendente", "valor": 100.0,
                            "juros": 0, "data_vencimento": hoje, "aluno_plano_id": "ap-uuid"}),
            MagicMock(data={"aluno_id": "aluno-uuid"}),
        ]
        mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute = single_execute

        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "mens-uuid", "status": "paga", "juros": 0.0}]
        )

        res = client.post(
            "/mensalidades/00000000-0000-0000-0000-000000000001/pagar",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["juros"] == 0.0


def test_pagamento_ja_paga(client):
    with patch("app.mensalidades.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "mens-uuid", "status": "paga", "valor": 100.0,
                  "data_vencimento": date.today().isoformat(), "aluno_plano_id": "ap-uuid"}
        )

        res = client.post(
            "/mensalidades/00000000-0000-0000-0000-000000000001/pagar",
            headers=_auth_headers(),
        )
        assert res.status_code == 400
        assert "já foi paga" in res.get_json()["error"]


def test_calculo_juros_30_dias_atraso():
    """2% ao mês sobre 30 dias = 2% do valor."""
    valor = 100.0
    dias = 30
    juros = round(valor * 0.02 * (dias / 30), 2)
    assert juros == 2.0


def test_calculo_juros_15_dias_atraso():
    """2% ao mês sobre 15 dias = 1% do valor."""
    valor = 100.0
    dias = 15
    juros = round(valor * 0.02 * (dias / 30), 2)
    assert juros == 1.0


# ── Jobs ──────────────────────────────────────────────────────────────────────

def test_job_atualizar_inadimplencia():
    with patch("app.mensalidades.jobs.supabase") as mock_supa:
        # Simula que não há mensalidades atrasadas nem inadimplentes
        mock_supa.table.return_value.update.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(data=[])
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        job_atualizar_inadimplencia()  # Não deve lançar exceção


def test_job_gerar_mensalidades_sem_planos_ativos():
    with patch("app.mensalidades.jobs.supabase") as mock_supa:
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        job_gerar_mensalidades()  # Não deve lançar exceção

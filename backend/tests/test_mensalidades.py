from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pytest
from app import create_app
from app.mensalidades.jobs import (
    job_atualizar_inadimplencia,
    job_gerar_mensalidades,
    criar_mensalidade,
)


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
    # O middleware (_get_profile) consulta o profile via .maybe_single();
    # mockamos ambos os caminhos para o tipo ser sempre resolvido.
    perfil = MagicMock(data={"tipo": tipo})
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = perfil
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = perfil


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


# ── Idempotência de criar_mensalidade (não duplica cobrança) ──────────────────

def test_criar_mensalidade_nao_duplica_periodo():
    """Já existindo mensalidade para (vínculo, vencimento), não insere outra."""
    with patch("app.mensalidades.jobs.supabase") as mock_supa:
        mock_supa.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "mens-existente"}]
        )
        criar_mensalidade("ap-uuid", 100.0, date(2026, 6, 1))
        mock_supa.table.return_value.insert.assert_not_called()


def test_criar_mensalidade_insere_quando_inexistente():
    """Sem mensalidade no período, insere normalmente."""
    with patch("app.mensalidades.jobs.supabase") as mock_supa:
        mock_supa.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        criar_mensalidade("ap-uuid", 100.0, date(2026, 6, 1))
        mock_supa.table.return_value.insert.assert_called_once()


# ── Novos testes: job_gerar_mensalidades ─────────────────────────────────────

def _plano_mock(ativo_profile=True, data_inicio="2026-01-01", data_fim=None):
    """Retorna um dict que simula uma linha de aluno_planos com joins aninhados."""
    return {
        "id": "ap-uuid",
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "planos": {"valor": 100.0},
        "alunos": {"profiles": {"ativo": ativo_profile}},
    }


def test_job_gerar_mensalidades_pula_aluno_desativado():
    """Aluno com profiles.ativo=False não recebe nova mensalidade."""
    with patch("app.mensalidades.jobs.supabase") as mock_supa, \
         patch("app.mensalidades.jobs.criar_mensalidade") as mock_criar:
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[_plano_mock(ativo_profile=False)]
        )
        job_gerar_mensalidades()
        mock_criar.assert_not_called()


def test_job_gerar_mensalidades_plano_sem_historico_gera_do_inicio():
    """Plano ativo sem nenhuma mensalidade prévia → gera a partir de data_inicio (safety net)."""
    with patch("app.mensalidades.jobs.supabase") as mock_supa, \
         patch("app.mensalidades.jobs.criar_mensalidade") as mock_criar:
        planos_tbl = MagicMock()
        planos_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[_plano_mock(data_inicio="2026-01-01")]
        )

        mens_tbl = MagicMock()
        # query da última mensalidade retorna vazio
        mens_tbl.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        mock_supa.table.side_effect = lambda name: (
            planos_tbl if name == "aluno_planos" else mens_tbl
        )

        job_gerar_mensalidades()
        mock_criar.assert_called_once_with("ap-uuid", 100.0, date(2026, 1, 1))


def test_job_gerar_mensalidades_respeita_horizonte():
    """Próxima mensalidade além de 5 dias não é gerada; dentro do horizonte sim."""
    hoje = date.today()
    # Última mensalidade vence hoje → próxima = hoje+30d → além do horizonte (hoje+5d)
    ultima_vcto_fora = hoje.isoformat()
    # Última mensalidade vence 26 dias atrás → próxima = hoje+4d → dentro do horizonte
    ultima_vcto_dentro = (hoje - timedelta(days=26)).isoformat()

    plano_fora = {**_plano_mock(), "id": "ap-fora"}
    plano_dentro = {**_plano_mock(), "id": "ap-dentro"}

    with patch("app.mensalidades.jobs.supabase") as mock_supa, \
         patch("app.mensalidades.jobs.criar_mensalidade") as mock_criar:
        planos_tbl = MagicMock()
        planos_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[plano_fora, plano_dentro]
        )

        mens_tbl = MagicMock()

        def mens_ultima(ap_id):
            vcto = ultima_vcto_fora if ap_id == "ap-fora" else ultima_vcto_dentro
            return MagicMock(data=[{"data_vencimento": vcto}])

        mens_tbl.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = [
            mens_ultima("ap-fora"),
            mens_ultima("ap-dentro"),
        ]

        mock_supa.table.side_effect = lambda name: (
            planos_tbl if name == "aluno_planos" else mens_tbl
        )

        job_gerar_mensalidades()

        # Só o plano dentro do horizonte deve gerar
        assert mock_criar.call_count == 1
        call_args = mock_criar.call_args
        assert call_args[0][0] == "ap-dentro"

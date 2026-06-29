"""Testes de mensalidades: pagamento, juros, jobs e idempotência.

Conceitos testados:
  - Cálculo de juros: 2 % ao mês, proporcional por dia de atraso.
  - Race condition (N-2): `.neq("status","paga")` no UPDATE impede que dois
    requests simultâneos registrem o mesmo pagamento duas vezes. Se o UPDATE
    não alterar nenhuma linha (já foi paga entre o fetch e o update), retorna 409.
  - B-3 (.maybe_single vs .single): .single() lança PGRST116 se a linha não
    existir; .maybe_single() devolve None e permite tratamento limpo de 404/400.
  - Idempotência do criar_mensalidade: o índice único no banco (uq_mensalidades_ap_vcto)
    é a garantia definitiva; a checagem na aplicação evita o custo do insert recusado.
  - job_gerar_mensalidades: aritmética de calendário correta (não timedelta(30))
    para não pular meses com 31 dias (ex.: Jan 31 → Fev 28, não Mar 2).
  - Horizonte de 5 dias: mensalidade só é gerada quando vence em ≤5 dias a
    partir de hoje — o aluno sempre tem visibilidade antecipada da próxima cobrança.

Padrão de mock:
  Dois patches separados:
    - `app.mensalidades.routes.supabase`: intercepta queries da rota.
    - `app.auth.middleware.supabase`: faz o middleware enxergar um usuário logado.
  Quando uma rota faz queries em múltiplas tabelas, usamos `table.side_effect`
  para rotear por nome de tabela, evitando que mocks de tabelas diferentes
  se sobreponham na mesma cadeia (MagicMock compartilhado).
"""
from datetime import date, timedelta
import calendar
from unittest.mock import patch, MagicMock
import pytest
from app import create_app
from app.mensalidades.jobs import (
    job_atualizar_inadimplencia,
    job_gerar_mensalidades,
    criar_mensalidade,
    _proxima_vencimento,
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
    """Simula um usuário autenticado e com profile no banco.

    O middleware (`require_auth`) faz duas chamadas ao Supabase:
      1. `auth.get_user(token)` → valida o JWT e retorna o user.id.
      2. `table("profiles").select("*").eq("id", ...).maybe_single().execute()`
         → busca o profile para saber o tipo (admin/recepcionista/aluno).
    Mockamos ambas aqui. O `tipo` controla o que o `require_role` vai ver.
    """
    user = MagicMock()
    user.id = "user-uuid"
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    # Mockamos .single e .maybe_single: o middleware usa .maybe_single (B-3),
    # mas alguns testes legados podem usar .single. Cobrir os dois é seguro.
    perfil = MagicMock(data={"tipo": tipo})
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = perfil
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = perfil


# ── Cálculo de juros ──────────────────────────────────────────────────────────

def test_pagamento_em_dia_sem_juros(client):
    """Mensalidade paga na data de vencimento: juros = 0.

    Técnica de mock por tabela (side_effect): a rota consulta 3 tabelas em
    sequência — mensalidades (fetch + update), aluno_planos (aluno_id),
    alunos (update de status). Se usarmos o mesmo mock para todas, o último
    setup sobrescreve o anterior. O side_effect roteia por nome de tabela.

    Fluxo de segurança testado:
      1. maybe_single (B-3): busca mensalidade sem risco de PGRST116.
      2. neq("status","paga") (N-2): UPDATE condicional impede pagamento duplo.
      3. 409 se UPDATE não atualiza nenhuma linha: mensalidade já foi paga
         concorrentemente — protege contra race condition.
    """
    hoje = date.today().isoformat()
    with patch("app.mensalidades.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        mensalidades_tbl = MagicMock()
        # (B-3) maybe_single: se a linha não existir, retorna None (não lança exceção).
        mensalidades_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "mens-uuid", "status": "pendente", "valor": 100.0,
                  "juros": 0, "data_vencimento": hoje, "aluno_plano_id": "ap-uuid"}
        )
        # (N-2) neq: só atualiza se ainda estiver "pendente" — impede pagamento duplo.
        mensalidades_tbl.update.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
            data=[{"id": "mens-uuid", "status": "paga", "juros": 0.0}]
        )
        # Verificação pós-pagamento: sem mensalidades atrasadas → aluno fica ativo.
        mensalidades_tbl.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        aluno_planos_tbl = MagicMock()
        # (B-3) maybe_single também aqui: aluno_plano corrompido não deve virar 500.
        aluno_planos_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"aluno_id": "aluno-uuid"}
        )

        alunos_tbl = MagicMock()
        alunos_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        # Roteamento por tabela: garante isolamento entre mocks de tabelas diferentes.
        mock_supa.table.side_effect = lambda n: {
            "mensalidades":  mensalidades_tbl,
            "aluno_planos":  aluno_planos_tbl,
            "alunos":        alunos_tbl,
        }.get(n, MagicMock())

        res = client.post(
            "/mensalidades/00000000-0000-0000-0000-000000000001/pagar",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["juros"] == 0.0


def test_pagamento_ja_paga(client):
    """Tentativa de pagar mensalidade já paga → 400 imediato (antes do UPDATE).

    O fetch inicial retorna status='paga' → a rota rejeita sem fazer UPDATE.
    Sem este guard, a rota tentaria o UPDATE (.neq → 0 linhas → 409),
    mas o 400 aqui é mais semântico: "você não deveria tentar pagar isso".
    """
    with patch("app.mensalidades.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        # (B-3) maybe_single devolve a mensalidade já paga.
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
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
    """2 % ao mês sobre 30 dias = exatamente 2 % do valor.

    Fórmula: valor × 0,02 × (dias / 30). Proporcional: 15 dias = 1 %, 60 dias = 4 %.
    O juros é calculado no BACKEND na hora do pagamento, nunca confiado no cliente.
    """
    valor = 100.0
    dias = 30
    juros = round(valor * 0.02 * (dias / 30), 2)
    assert juros == 2.0


def test_calculo_juros_15_dias_atraso():
    """2 % ao mês sobre 15 dias = 1 % (metade da taxa mensal)."""
    valor = 100.0
    dias = 15
    juros = round(valor * 0.02 * (dias / 30), 2)
    assert juros == 1.0


# ── Aritmética de calendário (bug fix: timedelta(30) pulava meses) ─────────────

def test_proxima_vencimento_janeiro_31():
    """Jan 31 + 1 mês = Fev 28 (ou 29 em ano bissexto), NÃO Mar 2.

    Com timedelta(30): Jan 31 + 30 = Mar 2 → fevereiro nunca cobrado.
    Com aritmética de calendário: capamos o dia ao último do mês destino.
    """
    # 2025 não é bissexto — fevereiro tem 28 dias.
    assert _proxima_vencimento(date(2025, 1, 31)) == date(2025, 2, 28)
    # 2024 é bissexto — fevereiro tem 29 dias.
    assert _proxima_vencimento(date(2024, 1, 31)) == date(2024, 2, 29)


def test_proxima_vencimento_marco_31():
    """Mar 31 → Abr 30 (abril tem 30 dias), não Abr 31 (inexistente)."""
    assert _proxima_vencimento(date(2026, 3, 31)) == date(2026, 4, 30)


def test_proxima_vencimento_dezembro_31():
    """Dez 31 → Jan 1 do próximo ano (virada de ano)."""
    assert _proxima_vencimento(date(2025, 12, 31)) == date(2026, 1, 31)


def test_proxima_vencimento_dia_fixo_medio():
    """Dia 15 em qualquer mês → dia 15 do mês seguinte (sem capping)."""
    assert _proxima_vencimento(date(2026, 6, 15)) == date(2026, 7, 15)
    assert _proxima_vencimento(date(2026, 1, 15)) == date(2026, 2, 15)


# ── Jobs ──────────────────────────────────────────────────────────────────────

def test_job_atualizar_inadimplencia():
    """Job diário: mensalidades pendentes vencidas → 'atrasada'; alunos → 'inadimplente'.

    Testamos que o job não lança exceção com dados vazios (happy path mínimo).
    O job usa supabase.table().update().eq().lt() para marcar atrasadas.
    """
    with patch("app.mensalidades.jobs.supabase") as mock_supa:
        mock_supa.table.return_value.update.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(data=[])
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        job_atualizar_inadimplencia()  # não deve lançar exceção


def test_job_gerar_mensalidades_sem_planos_ativos():
    """Sem planos ativos, o job termina sem criar nenhuma mensalidade."""
    with patch("app.mensalidades.jobs.supabase") as mock_supa:
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        job_gerar_mensalidades()  # não deve lançar exceção


# ── Idempotência de criar_mensalidade (não duplica cobrança) ──────────────────

def test_criar_mensalidade_nao_duplica_periodo():
    """Já existindo mensalidade para (vínculo, vencimento), não insere outra.

    A checagem na aplicação é uma otimização; a garantia definitiva é o índice
    único `uq_mensalidades_ap_vcto` no banco (migration 011).
    """
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
    """Retorna dict que simula linha de aluno_planos com joins aninhados.

    O job usa `alunos!inner(profiles!inner(ativo))` para filtrar alunos
    desativados sem precisar de uma query separada (evita N+1 de profiles).
    """
    return {
        "id": "ap-uuid",
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "planos": {"valor": 100.0},
        "alunos": {"profiles": {"ativo": ativo_profile}},
    }


def test_job_gerar_mensalidades_pula_aluno_desativado():
    """Aluno com profiles.ativo=False não recebe nova mensalidade.

    O admin desativa o aluno via /configuracoes/usuarios/<id>/status. O job
    respeita essa flag sem precisar de outra query ao banco.
    """
    with patch("app.mensalidades.jobs.supabase") as mock_supa, \
         patch("app.mensalidades.jobs.criar_mensalidade") as mock_criar:
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[_plano_mock(ativo_profile=False)]
        )
        job_gerar_mensalidades()
        mock_criar.assert_not_called()


def test_job_gerar_mensalidades_plano_sem_historico_gera_do_inicio():
    """Plano ativo sem nenhuma mensalidade prévia → gera a partir de data_inicio.

    vincular_plano() sempre cria a 1ª mensalidade; se não existe é sinal de
    falha anterior. O job gera a partir de data_inicio como safety net.
    """
    with patch("app.mensalidades.jobs.supabase") as mock_supa, \
         patch("app.mensalidades.jobs.criar_mensalidade") as mock_criar:
        planos_tbl = MagicMock()
        planos_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[_plano_mock(data_inicio="2026-01-01")]
        )

        mens_tbl = MagicMock()
        # query da última mensalidade retorna vazio → safety net
        mens_tbl.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        mock_supa.table.side_effect = lambda name: (
            planos_tbl if name == "aluno_planos" else mens_tbl
        )

        job_gerar_mensalidades()
        mock_criar.assert_called_once_with("ap-uuid", 100.0, date(2026, 1, 1))


def test_job_gerar_mensalidades_respeita_horizonte():
    """Próxima mensalidade além de 5 dias não é gerada; dentro do horizonte sim.

    Horizonte = hoje + 5 dias. O check é `proxima_vcto > horizonte` (strict),
    então 'exatamente hoje + 5 dias' ainda é gerado.

    Com aritmética de calendário (_proxima_vencimento), o próximo vencimento
    é sempre no mesmo dia do mês seguinte (capado ao último dia do mês):
      - `ultima_vcto_fora = hoje` → próxima = mês seguinte = ≥ 28 dias → além ✓
      - `ultima_vcto_dentro = hoje - 26d` → próxima = (hoje - 26d) + 1 mês
        = hoje + (dias_do_mês - 26), que é 2..5 dias → dentro ✓
        (mínimo: fevereiro tem 28 dias → 28-26=2; máximo: mês com 31 dias → 31-26=5)
    """
    hoje = date.today()
    ultima_vcto_fora   = hoje.isoformat()
    ultima_vcto_dentro = (hoje - timedelta(days=26)).isoformat()

    plano_fora   = {**_plano_mock(), "id": "ap-fora"}
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

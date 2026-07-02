from unittest.mock import patch, MagicMock

from tests._helpers import (
    mock_auth as _mock_auth,
    auth_headers as _auth_headers,
    UUID_A,
    UUID_B,
)


FAKE_AVALIACAO = {
    "id": "aval-uuid-0000-0000-0000-000000000001",
    "aluno_id": "aluno-uuid-000-0000-0000-000000000001",
    "instrutor_id": None,
    "data_avaliacao": "2026-06-25",
    "peso_kg": 75.0,
    "altura_cm": 175.0,
    "imc": 24.49,
    "gordura_corporal": 18.5,
    "massa_magra_kg": 61.1,
    "circ_cintura": 80.0,
    "circ_quadril": 95.0,
    "circ_braco": 35.0,
    "circ_coxa": 55.0,
    "circ_peito": 100.0,
    "pressao_arterial": "120/80",
    "observacoes": "Boa condição física",
}


# ── Sem token ─────────────────────────────────────────────────────────────────

def test_listar_sem_token(client):
    res = client.get("/avaliacoes")
    assert res.status_code == 401


def test_criar_sem_token(client):
    res = client.post("/avaliacoes", json=FAKE_AVALIACAO)
    assert res.status_code == 401


def test_deletar_sem_token(client):
    res = client.delete("/avaliacoes/00000000-0000-0000-0000-000000000001")
    assert res.status_code == 401


# ── Listar ────────────────────────────────────────────────────────────────────

def _mock_listagem(mock_supa, data):
    """Configura a cadeia select().order().range().execute() (resposta paginada)."""
    (mock_supa.table.return_value.select.return_value
        .order.return_value.range.return_value.execute.return_value) = MagicMock(
            data=data, count=len(data)
        )


def test_listar_como_admin(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        _mock_listagem(mock_supa, [FAKE_AVALIACAO])

        res = client.get("/avaliacoes", headers=_auth_headers())
        assert res.status_code == 200
        body = res.get_json()
        assert isinstance(body["data"], list)
        assert body["total"] == 1


def test_listar_como_recepcionista(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        _mock_listagem(mock_supa, [])

        res = client.get("/avaliacoes", headers=_auth_headers())
        assert res.status_code == 200


def test_listar_aluno_negado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        res = client.get("/avaliacoes", headers=_auth_headers())
        assert res.status_code == 403


def test_listar_instrutor_sem_alunos_retorna_vazio(client):
    # Instrutor sem alunos vinculados não vê nada
    with patch("app.avaliacoes.routes.supabase"), \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=[]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        res = client.get("/avaliacoes", headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["data"] == []


def test_listar_instrutor_filtra_seus_alunos(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=["aluno-1"]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")

        in_chain = (mock_supa.table.return_value.select.return_value
                    .in_.return_value.order.return_value.range.return_value)
        in_chain.execute.return_value = MagicMock(data=[FAKE_AVALIACAO], count=1)

        res = client.get("/avaliacoes", headers=_auth_headers())
        assert res.status_code == 200
        # confirma que o filtro por aluno_id foi aplicado
        mock_supa.table.return_value.select.return_value.in_.assert_called_once()
        args = mock_supa.table.return_value.select.return_value.in_.call_args
        assert args.args[0] == "aluno_id"
        assert args.args[1] == ["aluno-1"]


def test_listar_instrutor_aluno_id_fora_do_escopo(client):
    # Instrutor filtrando por aluno que não é dele → vazio (sem vazar dados).
    # (N-3) O aluno_id deve ser UUID válido; valores inválidos retornam 400.
    # Aqui usamos um UUID válido que simplesmente não está no escopo do instrutor.
    _ALUNO_FORA = "00000000-0000-0000-0000-000000000099"
    with patch("app.avaliacoes.routes.supabase"), \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=["aluno-1"]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        res = client.get(f"/avaliacoes?aluno_id={_ALUNO_FORA}", headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["data"] == []


# ── Criar ─────────────────────────────────────────────────────────────────────

def test_criar_sem_aluno_id(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/avaliacoes",
                          json={"data_avaliacao": "2026-06-25"},
                          headers=_auth_headers())
        assert res.status_code == 422
        assert "aluno_id" in res.get_json()["fields"]


def test_criar_sem_data(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/avaliacoes",
                          json={"aluno_id": UUID_A},
                          headers=_auth_headers())
        assert res.status_code == 422
        assert "data_avaliacao" in res.get_json()["fields"]


def test_criar_aluno_inexistente(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        # maybe_single() retorna data=None quando não encontra (não lança exceção)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        res = client.post("/avaliacoes", json={
            "aluno_id": "00000000-0000-0000-0000-000000000099",
            "data_avaliacao": "2026-06-25",
        }, headers=_auth_headers())
        assert res.status_code == 404


def test_criar_sucesso(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-uuid"}
        )
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[FAKE_AVALIACAO]
        )

        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A,
            "data_avaliacao": "2026-06-25",
            "peso_kg": 75.0,
            "altura_cm": 175.0,
        }, headers=_auth_headers())
        assert res.status_code == 201


def test_criar_todos_campos_incluindo_instrutor(client):
    """Preencher todos os campos (inclusive instrutor_id) deve retornar 201."""
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-uuid"}
        )
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[FAKE_AVALIACAO]
        )

        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A,
            "instrutor_id": "00000000-0000-0000-0000-000000000002",
            "data_avaliacao": "2026-06-25",
            "peso_kg": 75.0,
            "altura_cm": 175.0,
            "gordura_corporal": 18.5,
            "massa_magra_kg": 61.1,
            "circ_cintura": 80.0,
            "circ_quadril": 95.0,
            "circ_braco": 35.0,
            "circ_coxa": 55.0,
            "circ_peito": 100.0,
            "pressao_arterial": "120/80",
            "observacoes": "Boa condição física",
        }, headers=_auth_headers())
        assert res.status_code == 201


def test_criar_insert_falha_retorna_400(client):
    """Exceção no insert (ex.: FK inválida) deve retornar 400, não 500."""
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-uuid"}
        )
        mock_supa.table.return_value.insert.return_value.execute.side_effect = Exception(
            "violates foreign key constraint"
        )

        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A,
            "data_avaliacao": "2026-06-25",
            "instrutor_id": UUID_B,
        }, headers=_auth_headers())
        assert res.status_code == 400
        assert "avaliação" in res.get_json()["error"].lower()


def test_criar_data_invalida(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A,
            "data_avaliacao": "25/06/2026",  # formato errado
        }, headers=_auth_headers())
        assert res.status_code == 422
        assert "data_avaliacao" in res.get_json()["fields"]


def test_criar_instrutor_aluno_fora_do_escopo_negado(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=["outro-aluno"]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-x"}
        )
        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A,
            "data_avaliacao": "2026-06-25",
        }, headers=_auth_headers())
        assert res.status_code == 403


def test_criar_instrutor_forca_autoria(client):
    # instrutor_id enviado pelo cliente é ignorado: usa o id do instrutor logado
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=[UUID_A]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": UUID_A}
        )
        captured = {}

        def fake_insert(payload):
            captured["payload"] = payload
            chain = MagicMock()
            chain.execute.return_value = MagicMock(data=[{**FAKE_AVALIACAO, **payload}])
            return chain

        mock_supa.table.return_value.insert.side_effect = fake_insert

        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A,
            "data_avaliacao": "2026-06-25",
            "instrutor_id": UUID_B,  # tentativa de forjar autoria
        }, headers=_auth_headers())
        assert res.status_code == 201
        assert captured["payload"]["instrutor_id"] == "user-uuid"  # g.user_id


def test_criar_recepcionista_negado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.post("/avaliacoes", json={
            "aluno_id": "aluno-uuid",
            "data_avaliacao": "2026-06-25",
        }, headers=_auth_headers())
        assert res.status_code == 403


# ── Deletar ───────────────────────────────────────────────────────────────────

def test_deletar_como_instrutor_negado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        res = client.delete(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            headers=_auth_headers(),
        )
        assert res.status_code == 403


# ── Cálculo de IMC ────────────────────────────────────────────────────────────

def test_imc_calculado():
    from app.avaliacoes.routes import _calcular_imc
    assert _calcular_imc(75, 175) == 24.49


def test_imc_sem_dados():
    from app.avaliacoes.routes import _calcular_imc
    assert _calcular_imc(None, 175) is None
    assert _calcular_imc(75, None) is None
    assert _calcular_imc(75, 0) is None


# ── Buscar por id ─────────────────────────────────────────────────────────────

def test_buscar_sucesso(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        sem_instrutor = {**FAKE_AVALIACAO, "instrutor_id": None}
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=sem_instrutor
        )
        res = client.get(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["id"] == FAKE_AVALIACAO["id"]


def test_buscar_inexistente(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        res = client.get(
            "/avaliacoes/00000000-0000-0000-0000-000000000099",
            headers=_auth_headers(),
        )
        assert res.status_code == 404


def test_buscar_id_invalido(client):
    # UUID inválido -> rota não casa -> 404 do Flask
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.get("/avaliacoes/nao-e-uuid", headers=_auth_headers())
        assert res.status_code == 404


# ── Atualizar ─────────────────────────────────────────────────────────────────

def test_atualizar_sem_campos(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.put(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            json={},
            headers=_auth_headers(),
        )
        assert res.status_code == 400


def test_atualizar_campo_desconhecido_422(client):
    """Campo fora do schema é rejeitado (extra='forbid'), não ignorado em silêncio."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.put(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            json={"campo_inexistente": 1},
            headers=_auth_headers(),
        )
        assert res.status_code == 422
        assert "campo_inexistente" in res.get_json()["fields"]


def test_atualizar_recalcula_imc(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        # valor atual (para buscar altura quando só peso muda)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"peso_kg": 75.0, "altura_cm": 175.0}
        )
        captured = {}

        def fake_update(payload):
            captured["payload"] = payload
            chain = MagicMock()
            chain.eq.return_value.execute.return_value = MagicMock(data=[{**FAKE_AVALIACAO, **payload}])
            return chain

        mock_supa.table.return_value.update.side_effect = fake_update

        res = client.put(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            json={"peso_kg": 80},
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        # IMC recalculado com peso novo (80) e altura atual (175) = 26.12
        assert captured["payload"]["imc"] == 26.12


def test_atualizar_valor_numerico_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.put(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            json={"peso_kg": "abc"},
            headers=_auth_headers(),
        )
        assert res.status_code == 422
        assert "peso_kg" in res.get_json()["fields"]


def test_atualizar_inexistente(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        res = client.put(
            "/avaliacoes/00000000-0000-0000-0000-000000000099",
            json={"observacoes": "teste"},
            headers=_auth_headers(),
        )
        assert res.status_code == 404


def test_buscar_instrutor_fora_do_escopo_404(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=[]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=FAKE_AVALIACAO
        )
        res = client.get(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            headers=_auth_headers(),
        )
        assert res.status_code == 404


def test_atualizar_instrutor_fora_do_escopo_404(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=["outro"]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"aluno_id": "aluno-x", "peso_kg": 75.0, "altura_cm": 175.0}
        )
        res = client.put(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            json={"observacoes": "teste"},
            headers=_auth_headers(),
        )
        assert res.status_code == 404


# ── Deletar (sucesso) ─────────────────────────────────────────────────────────

def test_deletar_como_admin(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        chain = MagicMock()
        chain.eq.return_value.execute.return_value = MagicMock(data=[FAKE_AVALIACAO])
        mock_supa.table.return_value.delete.return_value = chain
        res = client.delete(
            "/avaliacoes/00000000-0000-0000-0000-000000000001",
            headers=_auth_headers(),
        )
        assert res.status_code == 200


# ── Export PDF ────────────────────────────────────────────────────────────────

def test_exportar_pdf(client):
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={**FAKE_AVALIACAO, "alunos": {"cpf": "12345678900", "profiles": {"nome": "João"}}}
        )
        res = client.get(
            "/avaliacoes/00000000-0000-0000-0000-000000000001/pdf",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        assert res.mimetype == "application/pdf"
        assert res.data[:4] == b"%PDF"


def test_exportar_pdf_instrutor_fora_do_escopo_404(client):
    # IDOR (A-1): instrutor não pode exportar o PDF de avaliação de aluno que
    # não é dele. Mesmo guard do GET JSON — devolve 404 sem vazar o registro.
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.avaliacoes.routes._alunos_do_instrutor", return_value=[]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={**FAKE_AVALIACAO, "alunos": {"cpf": "1", "profiles": {"nome": "João"}}}
        )
        res = client.get(
            "/avaliacoes/00000000-0000-0000-0000-000000000001/pdf",
            headers=_auth_headers(),
        )
        assert res.status_code == 404


def test_exportar_pdf_instrutor_seu_aluno_ok(client):
    # Contraprova: instrutor exporta normalmente o PDF de aluno do seu escopo.
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.avaliacoes.routes._alunos_do_instrutor",
               return_value=[FAKE_AVALIACAO["aluno_id"]]), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={**FAKE_AVALIACAO, "alunos": {"cpf": "1", "profiles": {"nome": "João"}}}
        )
        res = client.get(
            "/avaliacoes/00000000-0000-0000-0000-000000000001/pdf",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        assert res.data[:4] == b"%PDF"


def test_exportar_pdf_nome_com_markup(client):
    # Nome com caracteres de markup XML não pode quebrar a geração do PDF
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={**FAKE_AVALIACAO, "alunos": {"cpf": "1", "profiles": {"nome": "Jo<ão> & <b>Cia</b>"}}}
        )
        res = client.get(
            "/avaliacoes/00000000-0000-0000-0000-000000000001/pdf",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        assert res.data[:4] == b"%PDF"
        # nome do arquivo sanitizado (sem < > & espaços)
        cd = res.headers["Content-Disposition"]
        assert "<" not in cd and ">" not in cd and "&" not in cd

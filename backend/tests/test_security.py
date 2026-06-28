"""Testes de segurança — a tabela de "testes simulados" da auditoria virou código.

Cada bloco corresponde a uma linha do checklist:
  - IDOR/BOLA (aluno acessa recurso alheio)
  - Controle de acesso por papel (endpoint admin)
  - Escalonamento de privilégio (PUT /auth/me trocando 'tipo')
  - Ausência/expiração/adulteração de token
  - SQL injection nos filtros (inócuo: PostgREST parametriza)
  - XSS em conteúdo armazenado (escape na geração do PDF + ausência de
    dangerouslySetInnerHTML no frontend)
  - Brute force de login (rate limit)

E também regressões dos fixes desta entrega:
  - M-1: erro 500/400 não vaza o texto cru da exceção
  - B-1: cabeçalhos de segurança presentes
  - B-4: query params malformados respondem 400 (não 500)
"""
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from gotrue.errors import AuthApiError

from app import create_app

UUID_A = "00000000-0000-0000-0000-00000000000a"
UUID_B = "00000000-0000-0000-0000-00000000000b"


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth_headers():
    return {"Authorization": "Bearer token-fake"}


def _mock_auth(mock_supa, tipo="admin"):
    """Faz o require_auth enxergar um usuário logado do tipo informado."""
    user = MagicMock()
    user.id = "user-uuid"
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    perfil = MagicMock(data={"tipo": tipo})
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = perfil
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = perfil


def _self_chain(execute_result):
    """Query builder fake: todo método encadeável devolve ele mesmo."""
    chain = MagicMock()
    for metodo in (
        "select", "eq", "neq", "ilike", "filter", "order", "range", "in_",
        "gte", "lte", "or_", "single", "maybe_single", "limit",
    ):
        getattr(chain, metodo).return_value = chain
    chain.execute.return_value = execute_result
    return chain


# ── IDOR / BOLA: aluno tentando ler recurso de outro ──────────────────────────

def test_idor_aluno_outro_aluno_404(client):
    """GET /alunos/<id> roda sob a identidade do usuário (RLS). Quando a RLS
    não devolve linha (aluno alheio), a resposta é 404 — não vaza o registro."""
    with patch("app.alunos.routes.get_user_client") as mock_uc, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_uc.return_value = db

        res = client.get(f"/alunos/{UUID_B}", headers=_auth_headers())
        assert res.status_code == 404
        mock_uc.assert_called_once()  # provou que usou o client sob RLS


def test_idor_mensalidade_alheia_404(client):
    """GET /mensalidades/<id> também passa pela RLS (get_user_client)."""
    with patch("app.mensalidades.routes.get_user_client") as mock_uc, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_uc.return_value = db

        res = client.get(f"/mensalidades/{UUID_B}", headers=_auth_headers())
        assert res.status_code == 404
        mock_uc.assert_called_once()


# ── Controle de acesso por papel ──────────────────────────────────────────────

def test_endpoint_admin_negado_para_recepcionista(client):
    """PATCH /configuracoes/usuarios/<id>/tipo exige admin → 403 p/ recepcionista."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.patch(
            f"/configuracoes/usuarios/{UUID_B}/tipo",
            json={"tipo": "admin"},
            headers=_auth_headers(),
        )
        assert res.status_code == 403


def test_endpoint_admin_negado_para_aluno(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        res = client.patch(
            f"/configuracoes/usuarios/{UUID_B}/status",
            json={"ativo": False},
            headers=_auth_headers(),
        )
        assert res.status_code == 403


# ── Escalonamento de privilégio via auto-edição de perfil ─────────────────────

def test_nao_escala_privilegio_via_put_me(client):
    """PUT /auth/me com 'tipo' é rejeitado (extra='forbid') → 422, sem trocar papel."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        res = client.put("/auth/me", json={"tipo": "admin"}, headers=_auth_headers())
        assert res.status_code == 422
        assert "tipo" in res.get_json()["fields"]


def test_nao_ativa_propria_conta_via_put_me(client):
    """Campo 'ativo' também não é auto-editável pelo /auth/me."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        res = client.put("/auth/me", json={"ativo": True}, headers=_auth_headers())
        assert res.status_code == 422
        assert "ativo" in res.get_json()["fields"]


# ── Token: ausente, adulterado/expirado ───────────────────────────────────────

ENDPOINTS_PROTEGIDOS = [
    ("get", "/auth/me"),
    ("get", "/alunos"),
    ("get", "/instrutores"),
    ("get", f"/mensalidades/{UUID_A}"),
    ("get", "/avaliacoes"),
    ("get", "/dashboard/alunos"),
    ("get", "/configuracoes/usuarios"),
    ("get", "/portal/me"),
    ("get", "/relatorios/alunos"),
]


@pytest.mark.parametrize("metodo,rota", ENDPOINTS_PROTEGIDOS)
def test_sem_token_401(client, metodo, rota):
    res = getattr(client, metodo)(rota)
    assert res.status_code == 401


def test_token_adulterado_ou_expirado_401(client):
    """Token inválido/expirado: get_user lança AuthApiError → 401."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        mock_auth.auth.get_user.side_effect = AuthApiError("invalid token", 401, {})
        res = client.get("/auth/me", headers={"Authorization": "Bearer adulterado"})
        assert res.status_code == 401


def test_header_authorization_malformado_401(client):
    """Sem o prefixo 'Bearer ' o token não é aceito."""
    res = client.get("/auth/me", headers={"Authorization": "token-sem-bearer"})
    assert res.status_code == 401


# ── SQL injection nos filtros (deve ser inócuo) ───────────────────────────────

def test_sql_injection_em_filtro_e_inocuo(client):
    """Payload de SQLi no filtro 'busca' é tratado como VALOR parametrizado
    (vai para o query builder do PostgREST), não concatenado em SQL cru."""
    payload_malicioso = "'; DROP TABLE alunos;--"
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        chain = _self_chain(MagicMock(data=[], count=0))
        mock_supa.table.return_value = chain

        res = client.get(
            "/alunos", query_string={"busca": payload_malicioso}, headers=_auth_headers()
        )
        assert res.status_code == 200
        # o texto malicioso foi passado como parâmetro de filtro, nunca como SQL
        assert chain.filter.called
        args = chain.filter.call_args.args
        assert payload_malicioso in args[-1]


# ── XSS em conteúdo armazenado ────────────────────────────────────────────────

def test_pdf_escapa_markup_no_nome(client):
    """Conteúdo com markup (XSS/markup do reportlab) não quebra o PDF e o nome
    do arquivo é sanitizado (sem < > & no Content-Disposition)."""
    aval = {
        "id": UUID_A, "aluno_id": UUID_B, "instrutor_id": None,
        "data_avaliacao": "2026-06-25", "imc": 24.0, "observacoes": "<script>x</script>",
        "alunos": {"cpf": "1", "profiles": {"nome": "Jo<ão> & <b>Cia</b>"}},
    }
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=aval
        )
        res = client.get(f"/avaliacoes/{UUID_A}/pdf", headers=_auth_headers())
        assert res.status_code == 200
        assert res.data[:4] == b"%PDF"
        cd = res.headers["Content-Disposition"]
        assert "<" not in cd and ">" not in cd and "&" not in cd


def test_frontend_sem_dangerouslysetinnerhtml():
    """Guarda: nenhum componente do frontend injeta HTML cru (vetor de XSS).

    Varre só o código-fonte (app/components/hooks/lib), ignorando artefatos de
    build (.next) e dependências (node_modules). Pulado se o frontend não existir."""
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    if not frontend.exists():
        pytest.skip("frontend não presente neste checkout")

    fontes = ["app", "components", "hooks", "lib"]
    ofensores = []
    for pasta in fontes:
        raiz = frontend / pasta
        if not raiz.exists():
            continue
        for ext in ("*.js", "*.jsx"):
            ofensores += [
                str(p) for p in raiz.rglob(ext)
                if "dangerouslySetInnerHTML" in p.read_text(encoding="utf-8", errors="ignore")
            ]
    assert not ofensores, f"dangerouslySetInnerHTML encontrado em: {ofensores}"


# ── M-1: respostas de erro não vazam detalhes internos ────────────────────────

def test_erro_500_nao_vaza_detalhe(client):
    """Em produção (debug=False) o handler 500 devolve mensagem genérica,
    sem o texto cru da exceção (que pode revelar schema/erros do PostgREST)."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False  # deixa o errorhandler(500) rodar
    segredo = "coluna secreta interna xyz"
    with app.test_client() as c, \
         patch("app.dashboard.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.side_effect = Exception(segredo)

        res = c.get("/dashboard/alunos", headers=_auth_headers())
        assert res.status_code == 500
        body = res.get_json()
        assert "detalhe" not in body
        assert segredo not in res.get_data(as_text=True)


def test_avaliacao_insert_falha_nao_vaza_detalhe(client):
    """Falha no insert vira 400 genérico, sem 'detalhe' nem texto da exceção."""
    segredo = "violates foreign key constraint fk_secreta"
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-uuid"}
        )
        mock_supa.table.return_value.insert.return_value.execute.side_effect = Exception(segredo)

        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A, "data_avaliacao": "2026-06-25",
        }, headers=_auth_headers())
        assert res.status_code == 400
        body = res.get_json()
        assert "detalhe" not in body
        assert segredo not in res.get_data(as_text=True)


# ── B-1: cabeçalhos de segurança ──────────────────────────────────────────────

def test_cabecalhos_seguranca_presentes(client):
    """Toda resposta (até a de 401) deve trazer os headers de segurança."""
    res = client.get("/auth/me")  # 401, mas o after_request roda mesmo assim
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "no-referrer"
    assert "default-src 'none'" in res.headers.get("Content-Security-Policy", "")


# ── B-2: limites de entrada nas avaliações ────────────────────────────────────

def test_avaliacao_observacoes_grande_demais_422(client):
    with patch("app.avaliacoes.routes.supabase"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A, "data_avaliacao": "2026-06-25",
            "observacoes": "x" * 5000,
        }, headers=_auth_headers())
        assert res.status_code == 422
        assert "observacoes" in res.get_json()["fields"]


def test_avaliacao_valor_fora_da_faixa_422(client):
    with patch("app.avaliacoes.routes.supabase"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/avaliacoes", json={
            "aluno_id": UUID_A, "data_avaliacao": "2026-06-25",
            "gordura_corporal": 250,  # > 100%
        }, headers=_auth_headers())
        assert res.status_code == 422
        assert "gordura_corporal" in res.get_json()["fields"]


# ── B-4: query params malformados respondem 400 (não 500) ─────────────────────

def test_mensalidades_mes_malformado_400(client):
    with patch("app.mensalidades.routes.supabase"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.get("/mensalidades", query_string={"mes": "junho/2026"}, headers=_auth_headers())
        assert res.status_code == 400
        assert "mes" in res.get_json()["error"].lower()


def test_relatorio_financeiro_mes_malformado_400(client):
    with patch("app.relatorios.routes.supabase"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.get(
            "/relatorios/financeiro",
            query_string={"formato": "pdf", "mes": "2026-13"},
            headers=_auth_headers(),
        )
        assert res.status_code == 400


def test_avaliacoes_data_malformada_400(client):
    with patch("app.avaliacoes.routes.supabase"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.get(
            "/avaliacoes", query_string={"data_inicio": "25-06-2026"}, headers=_auth_headers()
        )
        assert res.status_code == 400


# ── M-2: nenhuma rota fica sem autenticação por esquecimento ──────────────────

def test_toda_rota_protegida_exige_token(client):
    """Backstop: como o backend usa service_role (RLS desligado), a autorização
    depende inteiramente dos decorators. Se uma rota nova esquecer
    @require_auth/@require_role, ela responderia sem 401 — e este teste falha,
    pegando o erro antes de ir para produção."""
    app = client.application
    publicas = {("auth.login", "POST")}  # única rota sem token

    def concretizar(regra: str) -> str:
        def repl(m):
            token = m.group(0)
            if token.startswith("<int:"):
                return "1"
            if token.startswith("<uuid:"):
                return UUID_A
            return "x"
        return re.sub(r"<[^>]+>", repl, regra)

    faltando = []
    for regra in app.url_map.iter_rules():
        if regra.endpoint == "static":
            continue
        caminho = concretizar(regra.rule)
        for metodo in (regra.methods or set()) - {"OPTIONS", "HEAD"}:
            if (regra.endpoint, metodo) in publicas:
                continue
            resp = client.open(caminho, method=metodo)
            if resp.status_code != 401:
                faltando.append((metodo, regra.rule, resp.status_code))

    assert not faltando, f"Rotas que não exigiram token (auth ausente?): {faltando}"


# ── Brute force de login (rate limit) ─────────────────────────────────────────

def test_login_rate_limited():
    """Após exceder o limite, o login responde 429 (mitiga brute force)."""
    from app.extensions import limiter
    from app.config import Config

    app = create_app()
    app.config["TESTING"] = True
    original = Config.RATELIMIT_LOGIN
    Config.RATELIMIT_LOGIN = "2 per minute"
    app.config["RATELIMIT_ENABLED"] = True
    limiter.init_app(app)
    limiter.enabled = True
    try:
        with app.test_client() as c, \
             patch("app.auth.routes.get_anon_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.auth.sign_in_with_password.side_effect = AuthApiError(
                "Invalid login credentials", 400, {}
            )
            mock_factory.return_value = mock_client
            codes = [
                c.post("/auth/login", json={"email": "a@a.com", "password": "x"}).status_code
                for _ in range(3)
            ]
        assert codes[0] == 401
        assert codes[-1] == 429
    finally:
        Config.RATELIMIT_LOGIN = original
        limiter.enabled = False

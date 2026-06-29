"""Testes de segurança — a tabela de "testes simulados" da auditoria virou código.

Cada bloco cobre uma categoria do OWASP / auditoria interna:

  IDOR / BOLA (Broken Object Level Authorization)
    Um aluno autenticado não pode acessar o registro de OUTRO aluno.
    A proteção vem do `get_user_client(token)`: consulta o banco sob a
    IDENTIDADE do usuário logado, não com a service_role. O Supabase RLS
    filtra o que esse usuário pode ver. Se a RLS não devolve linha → 404.

  Controle de acesso por papel (RBAC)
    Endpoints de admin são decorados com @require_role("admin"). Papel
    inferior (recepcionista, aluno) recebe 403 antes de chegar ao handler.

  Escalonamento de privilégio via auto-edição de perfil (Mass Assignment)
    PUT /auth/me usa ProfileUpdateSchema com extra='forbid'. Se o cliente
    mandar 'tipo' ou 'ativo' no corpo, Pydantic rejeita com 422. Sem isso
    um aluno poderia escrever {"tipo": "admin"} e se promover.

  Token ausente / adulterado / expirado
    require_auth rejeita qualquer requisição sem header Authorization ou
    com um token que o Supabase Auth não reconhece como válido.

  SQL injection (inócuo com PostgREST)
    O PostgREST usa consultas parametrizadas — o valor do filtro nunca é
    concatenado em SQL cru. Um payload malicioso vai como string literal.

  XSS em conteúdo armazenado (Stored XSS)
    O nome do aluno é lido do banco e inserido no PDF via reportlab.
    O título usa xml_escape() para que '<' e '>' não quebrem o markup XML
    do reportlab. O nome do arquivo é sanitizado para evitar injeção no
    header Content-Disposition.

  Cabeçalhos de segurança HTTP (B-1)
    O after_request adiciona X-Content-Type-Options, X-Frame-Options, CSP
    e Referrer-Policy em TODA resposta — inclusive nas de 401.

  Brute force de login (rate limiting)
    @limiter.limit() conta tentativas por IP. Após o limite → 429.

  Backstop de autenticação (M-2)
    Varre todas as rotas registradas e verifica que nenhuma responde sem
    exigir token. Se uma nova rota esquecer @require_auth → este teste falha.

Padrão de mock:
  _mock_auth(mock_supa, tipo="...")  configura `app.auth.middleware.supabase`
    para simular um usuário logado com o tipo fornecido.
  _self_chain(result)  cria um mock "auto-retornante" onde qualquer método
    de query builder devolve a própria cadeia — útil para testar filtros
    sem precisar prever a ordem exata dos métodos chamados.
"""
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from gotrue.errors import AuthApiError

from app import create_app

# UUIDs fixos usados nos testes que precisam de path params com UUID válido.
# Flask converte <uuid:...> antes do handler — string não-UUID → 404 automático.
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
    """Faz require_auth enxergar um usuário logado do tipo informado.

    O middleware valida o JWT (auth.get_user) e busca o profile (.maybe_single).
    Mockamos os dois caminhos (.single e .maybe_single) para cobrir variações.
    """
    user = MagicMock()
    user.id = "user-uuid"
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    perfil = MagicMock(data={"tipo": tipo})
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = perfil
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = perfil


def _self_chain(execute_result):
    """Mock "auto-retornante": cada método da cadeia retorna a si mesmo.

    Útil para endpoints que aplicam filtros variáveis (busca, datas, etc.).
    Sem este helper, precisaríamos prever a sequência exata de métodos —
    o que quebraria se o handler mudar a ordem dos filtros.
    """
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
    """GET /alunos/<id> roda sob a identidade do usuário (RLS via get_user_client).

    RLS = Row Level Security. No Supabase, políticas RLS definem quais linhas
    cada usuário pode ver. Quando a RLS não devolve a linha (aluno alheio),
    a resposta é 404 — não vaza o registro.

    O `mock_uc.assert_called_once()` prova que o handler usou `get_user_client`
    (client com RLS), e não o `supabase` global (service_role, que ignora RLS).
    """
    with patch("app.alunos.routes.get_user_client") as mock_uc, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        db = MagicMock()
        # RLS não devolve linha para aluno alheio → data=None.
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_uc.return_value = db

        res = client.get(f"/alunos/{UUID_B}", headers=_auth_headers())
        assert res.status_code == 404
        mock_uc.assert_called_once()  # prova que usou client com RLS


def test_idor_mensalidade_alheia_404(client):
    """GET /mensalidades/<id> também usa get_user_client (RLS ativo).

    Sem a RLS, qualquer usuário autenticado (inclusive alunos) poderia
    ler mensalidades de outros apenas variando o UUID na URL.
    """
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
    """PATCH /configuracoes/usuarios/<id>/tipo exige admin → 403 para recepcionista.

    @require_role("admin") verifica g.user_tipo antes de executar o handler.
    O decorator é empilhado: require_role → require_auth → handler.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.patch(
            f"/configuracoes/usuarios/{UUID_B}/tipo",
            json={"tipo": "admin"},
            headers=_auth_headers(),
        )
        assert res.status_code == 403


def test_endpoint_admin_negado_para_aluno(client):
    """PATCH /configuracoes/usuarios/<id>/status: aluno não pode alterar status."""
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
    """PUT /auth/me com 'tipo' é rejeitado pelo schema (extra='forbid') → 422.

    ProfileUpdateSchema não declara o campo 'tipo'. Com extra='forbid', qualquer
    campo não declarado no schema causa ValidationError → 422 + lista de fields.
    Sem esta proteção, um aluno poderia escrever {"tipo":"admin"} e elevar o próprio papel.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        res = client.put("/auth/me", json={"tipo": "admin"}, headers=_auth_headers())
        assert res.status_code == 422
        assert "tipo" in res.get_json()["fields"]


def test_nao_ativa_propria_conta_via_put_me(client):
    """'ativo' também não é editável pelo próprio usuário.

    Sem este bloqueio, uma conta desativada pelo admin poderia reativar a si
    mesma mandando {"ativo": true} e contornando a medida administrativa.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        res = client.put("/auth/me", json={"ativo": True}, headers=_auth_headers())
        assert res.status_code == 422
        assert "ativo" in res.get_json()["fields"]


# ── Token: ausente, adulterado/expirado ───────────────────────────────────────

# Lista de endpoints que DEVEM exigir autenticação. Se uma nova rota for
# adicionada sem @require_auth, o teste de backstop (test_toda_rota_protegida_exige_token)
# vai pegar — mas esta lista serve como documentação das rotas críticas.
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
    """Requisição sem token → 401 (sem autenticação, sem dados)."""
    res = getattr(client, metodo)(rota)
    assert res.status_code == 401


def test_token_adulterado_ou_expirado_401(client):
    """Token inválido/expirado: auth.get_user lança AuthApiError → 401.

    O Supabase Auth valida a assinatura JWT. Um token adulterado ou expirado
    gera AuthApiError que o middleware captura e converte em 401 limpo.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        mock_auth.auth.get_user.side_effect = AuthApiError("invalid token", 401, {})
        res = client.get("/auth/me", headers={"Authorization": "Bearer adulterado"})
        assert res.status_code == 401


def test_header_authorization_malformado_401(client):
    """Sem o prefixo 'Bearer ' o token não é extraído → 401.

    _get_token() só aceita o formato 'Bearer <token>'. Outros formatos
    (Basic, Digest, token sem prefixo) são ignorados e tratados como ausência.
    """
    res = client.get("/auth/me", headers={"Authorization": "token-sem-bearer"})
    assert res.status_code == 401


# ── SQL injection nos filtros (deve ser inócuo) ───────────────────────────────

def test_sql_injection_em_filtro_e_inocuo(client):
    """Payload de SQLi no filtro 'busca' é tratado como valor parametrizado.

    O PostgREST gera consultas do tipo WHERE profiles.nome ILIKE $1 com o valor
    como parâmetro — nunca concatenado em SQL cru. O payload malicioso vai como
    string literal e é passado ao Postgres sem execução.

    O assert verifica que `chain.filter` foi chamado com o payload como argumento
    (prova que o valor não foi interpretado como SQL, apenas como dado de filtro).
    """
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
        # Prova que o valor malicioso foi passado COMO DADO de filtro, não como SQL.
        assert chain.filter.called
        args = chain.filter.call_args.args
        assert payload_malicioso in args[-1]


# ── XSS em conteúdo armazenado ────────────────────────────────────────────────

def test_pdf_escapa_markup_no_nome(client):
    """Conteúdo com markup não quebra o PDF e o nome do arquivo é sanitizado.

    Dois vetores de ataque cobertos:
      1. Título do PDF: reportlab interpreta markup XML — um '<' no nome do
         aluno quebraria a geração. xml_escape() converte para entidades HTML.
      2. Content-Disposition: o nome do arquivo é gerado a partir do nome do
         aluno. Caracteres especiais poderiam injetar headers HTTP. O handler
         usa um slug alfanumérico (só [a-zA-Z0-9_]) para o nome do arquivo.
    """
    aval = {
        "id": UUID_A, "aluno_id": UUID_B, "instrutor_id": None,
        "data_avaliacao": "2026-06-25", "imc": 24.0, "observacoes": "<script>x</script>",
        "alunos": {"cpf": "1", "profiles": {"nome": "Jo<ão> & <b>Cia</b>"}},
    }
    with patch("app.avaliacoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        # (B-3) maybe_single: busca a avaliação sem risco de PGRST116.
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=aval
        )
        res = client.get(f"/avaliacoes/{UUID_A}/pdf", headers=_auth_headers())
        assert res.status_code == 200
        assert res.data[:4] == b"%PDF"
        # O nome do arquivo no Content-Disposition não deve conter < > &.
        cd = res.headers["Content-Disposition"]
        assert "<" not in cd and ">" not in cd and "&" not in cd


def test_frontend_sem_dangerouslysetinnerhtml():
    """Guarda: nenhum componente do frontend injeta HTML cru (vetor de XSS).

    `dangerouslySetInnerHTML` é o mecanismo do React para injetar HTML sem
    escaping. Se usado com conteúdo do banco (ex.: observações de avaliação),
    permite Stored XSS — um aluno poderia guardar <script>... e executar
    código no navegador de outros usuários.

    Varre só o código-fonte (app/components/hooks/lib), ignorando artefatos de
    build (.next) e dependências (node_modules). Pulado se frontend não existir.
    """
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
    """Em produção (debug=False) o handler 500 devolve mensagem genérica.

    Detalhes de exceção internos (schema do banco, erros do PostgREST,
    nomes de colunas) não devem aparecer no body da resposta. O campo
    'detalhe' só é adicionado quando app.debug=True (ambiente de dev).
    """
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
        assert "detalhe" not in body                          # campo não existe em produção
        assert segredo not in res.get_data(as_text=True)     # texto da exceção não vaza


def test_avaliacao_insert_falha_nao_vaza_detalhe(client):
    """Falha no insert vira 400 genérico, sem 'detalhe' nem texto da exceção.

    O handler captura a exceção internamente (BLE001 suprimido no lint),
    loga para o operador e retorna mensagem sem informação estrutural do banco.
    """
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
    """Toda resposta (até a 401) traz os headers de segurança.

    O after_request em app/__init__.py adiciona:
      - X-Content-Type-Options: nosniff — impede MIME sniffing pelo navegador.
      - X-Frame-Options: DENY — impede clickjacking via <iframe>.
      - Referrer-Policy: no-referrer — não vaza a URL da API em redirects.
      - Content-Security-Policy — a API não serve HTML; nenhuma fonte externa.
    """
    res = client.get("/auth/me")  # 401, mas o after_request roda mesmo assim
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "no-referrer"
    assert "default-src 'none'" in res.headers.get("Content-Security-Policy", "")


# ── B-2: limites de entrada nas avaliações ────────────────────────────────────

def test_avaliacao_observacoes_grande_demais_422(client):
    """Observações com mais de 2000 chars → 422 antes de chegar ao banco.

    O schema _AvaliacaoMedidas declara `observacoes: Field(max_length=2000)`.
    Isso protege contra DoS por entrada enorme e espelha o CHECK do banco —
    assim a validação falha na borda (API) antes de chegar ao Postgres.
    """
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
    """Percentual de gordura corporal > 100 → 422 (fisicamente impossível).

    As faixas no schema espelham os CHECKs do banco e barram valores absurdos
    na borda — evitando que um 500 do Postgres vaze detalhes do schema.
    """
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
    """'mes' fora do formato AAAA-MM → 400 limpo, não 500.

    Um 'mes' malformado chegaria ao int(mes[:4]) e quebraria em TypeError ou
    causaria um erro de cast no Postgres. mes_valido() valida antes de montar
    o filtro de data, devolvendo 400 com mensagem controlada.
    """
    with patch("app.mensalidades.routes.supabase"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.get("/mensalidades", query_string={"mes": "junho/2026"}, headers=_auth_headers())
        assert res.status_code == 400
        assert "mes" in res.get_json()["error"].lower()


def test_relatorio_financeiro_mes_malformado_400(client):
    """Relatório financeiro com mês inválido → 400, não 500."""
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
    """Data no formato errado (DD-MM-AAAA em vez de AAAA-MM-DD) → 400.

    data_iso_valida() valida o formato antes de passar para o filtro PostgREST.
    Sem essa validação, o Postgres tentaria castear a string e falharia com
    um erro que o PostgREST expõe como 400 com o texto interno do banco.
    """
    with patch("app.avaliacoes.routes.supabase"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.get(
            "/avaliacoes", query_string={"data_inicio": "25-06-2026"}, headers=_auth_headers()
        )
        assert res.status_code == 400


# ── M-2: nenhuma rota fica sem autenticação por esquecimento ──────────────────

def test_toda_rota_protegida_exige_token(client):
    """Backstop: varre TODAS as rotas e verifica que exigem autenticação.

    Como o backend usa service_role (RLS desligado), a autorização depende
    inteiramente dos decorators (@require_auth / @require_role). Uma rota
    nova sem esses decorators ficaria pública — e este teste detecta antes
    de ir para produção. É o "cinturão" que complementa os "suspensórios".

    A função `concretizar` substitui parâmetros de rota (<uuid:...>, <int:...>)
    por valores válidos para que o Flask roteie corretamente a requisição.
    """
    app = client.application
    publicas = {
        ("auth.login", "POST"),  # login: único endpoint sem token
        ("health",     "GET"),   # /health: healthcheck público para Docker/monitoramento
    }

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
    """Após exceder o limite, o login responde 429 (mitiga brute force).

    Em testes o rate limit é desligado (RATELIMIT_ENABLED=False). Este teste
    religa explicitamente para validar o comportamento de 429.
    Em produção, o armazenamento deve ser Redis (não memory://) para que o
    limite seja compartilhado entre workers — evita bypass com múltiplos processos.
    """
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
        assert codes[0] == 401      # dentro do limite, credenciais inválidas
        assert codes[-1] == 429     # estourou o limite → bloqueado
    finally:
        Config.RATELIMIT_LOGIN = original
        limiter.enabled = False

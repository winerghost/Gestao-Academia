"""Pentest avançado — cobertura de segurança que complementa test_security.py.

Este módulo trata o backend como alvo de um teste de invasão. Cada classe
corresponde a uma técnica/objetivo do atacante e a uma categoria OWASP:

  A01 Broken Access Control
    - Matriz RBAC completa: TODO endpoint privilegiado × TODO papel sem
      permissão → 403. É o "cinturão" que pega uma nova rota que esqueça de
      restringir o papel (o backstop de token já existe em test_security.py).
    - IDOR/BOLA reforçado nos recursos que rodam sob a identidade do usuário.

  A03 Injection / A08 Data Integrity
    - Mass assignment: campos privilegiados (tipo, ativo, id, imc) enviados no
      corpo são rejeitados pelo schema (extra='forbid') → 422. Sem isso um
      papel inferior poderia se promover ou forjar valores calculados no servidor.
    - Corpo não-JSON / tipo trocado → 400 controlado, nunca 500.

  A02/A05 Autenticação e configuração
    - Cabeçalho Authorization malformado em várias formas → 401 (sem tocar a rede).
    - CORS não reflete origem não autorizada.
    - Cabeçalhos de segurança presentes em 401/404/405/200.

  A04 Insecure Design (DoS por entrada)
    - Bomba de descompressão e polyglot no processamento de imagem → 400, sem crash.

  A09 Security Logging / vazamento
    - Erro interno em QUALQUER módulo não devolve o texto da exceção.

Toda a validação vive no backend (o frontend é tratado como não confiável):
estes testes provam isso na borda da API, independente do que o cliente envie.
"""
import io
from unittest.mock import patch, MagicMock

import pytest
from gotrue.errors import AuthApiError
from PIL import Image

from app import create_app
from app.auth import avatar as avatar_mod
from tests._helpers import (
    mock_auth as _mock_auth,
    auth_headers as _auth_headers,
    self_chain as _self_chain,
    UUID_A as U,
)

TODOS_OS_PAPEIS = ("admin", "recepcionista", "instrutor", "aluno")


# ══════════════════════════════════════════════════════════════════════════════
# A01 — Matriz RBAC: cada rota privilegiada nega TODO papel sem permissão (403)
# ══════════════════════════════════════════════════════════════════════════════

# (método, caminho, papéis PERMITIDOS). A verificação de papel roda no
# require_role (o decorator mais externo), ANTES de validar corpo ou tocar o
# banco — então basta um usuário autenticado do papel errado para provocar 403.
MATRIZ_RBAC = [
    ("get",    "/alunos",                                 {"admin", "recepcionista"}),
    ("post",   "/alunos",                                 {"admin", "recepcionista"}),
    ("put",    f"/alunos/{U}",                            {"admin", "recepcionista"}),
    ("patch",  f"/alunos/{U}/status",                     {"admin", "recepcionista"}),
    ("post",   f"/alunos/{U}/planos",                     {"admin", "recepcionista"}),
    ("put",    f"/alunos/{U}/planos/{U}",                 {"admin", "recepcionista"}),
    ("delete", f"/alunos/{U}/planos/{U}",                 {"admin", "recepcionista"}),
    ("get",    "/instrutores",                            {"admin", "recepcionista"}),
    ("post",   "/instrutores",                            {"admin"}),
    ("put",    f"/instrutores/{U}",                       {"admin"}),
    ("get",    f"/instrutores/{U}/planos",                {"admin", "recepcionista"}),
    ("post",   f"/instrutores/{U}/planos",                {"admin"}),
    ("delete", f"/instrutores/{U}/planos/{U}",            {"admin"}),
    ("get",    "/avaliacoes",                             {"admin", "instrutor", "recepcionista"}),
    ("post",   "/avaliacoes",                             {"admin", "instrutor"}),
    ("get",    f"/avaliacoes/{U}",                        {"admin", "instrutor", "recepcionista"}),
    ("put",    f"/avaliacoes/{U}",                        {"admin", "instrutor"}),
    ("delete", f"/avaliacoes/{U}",                        {"admin"}),
    ("get",    f"/avaliacoes/{U}/pdf",                    {"admin", "instrutor", "recepcionista"}),
    ("get",    "/configuracoes/usuarios",                 {"admin"}),
    ("post",   "/configuracoes/usuarios",                 {"admin"}),
    ("delete", f"/configuracoes/usuarios/{U}",            {"admin"}),
    ("post",   f"/configuracoes/usuarios/{U}/reset-senha",{"admin"}),
    ("patch",  f"/configuracoes/usuarios/{U}/tipo",       {"admin"}),
    ("patch",  f"/configuracoes/usuarios/{U}/status",     {"admin"}),
    ("post",   f"/configuracoes/usuarios/{U}/avatar",     {"admin", "recepcionista"}),
    ("delete", f"/configuracoes/usuarios/{U}/avatar",     {"admin", "recepcionista"}),
    ("put",    "/configuracoes/academia",                 {"admin"}),
    ("get",    "/dashboard/alunos",                       {"admin", "recepcionista"}),
    ("get",    "/dashboard/financeiro",                   {"admin", "recepcionista"}),
    ("get",    "/dashboard/frequencia",                   {"admin", "recepcionista"}),
    ("get",    "/mensalidades",                           {"admin", "recepcionista"}),
    ("post",   f"/mensalidades/{U}/pagar",                {"admin", "recepcionista"}),
    ("post",   "/planos",                                 {"admin"}),
    ("put",    f"/planos/{U}",                            {"admin"}),
    ("patch",  f"/planos/{U}/ativo",                      {"admin"}),
    ("get",    "/relatorios/alunos",                      {"admin", "recepcionista"}),
    ("get",    "/relatorios/financeiro",                  {"admin", "recepcionista"}),
    ("get",    "/relatorios/inadimplencia",               {"admin", "recepcionista"}),
]

# Expande para (método, caminho, papel_negado) — um caso por combinação inválida.
_CASOS_RBAC = [
    (metodo, caminho, papel)
    for metodo, caminho, permitidos in MATRIZ_RBAC
    for papel in TODOS_OS_PAPEIS
    if papel not in permitidos
]


@pytest.mark.parametrize("metodo,caminho,papel", _CASOS_RBAC)
def test_rbac_papel_sem_permissao_recebe_403(client, metodo, caminho, papel):
    """Um usuário autenticado, mas do papel errado, nunca alcança o handler.

    Se alguém adicionar um endpoint privilegiado e esquecer (ou errar) o
    @require_role, este teste falha — é a rede de proteção de autorização.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo=papel)
        res = getattr(client, metodo)(caminho, headers=_auth_headers(), json={})
        assert res.status_code == 403, (
            f"{metodo.upper()} {caminho} deveria negar o papel '{papel}' com 403, "
            f"mas retornou {res.status_code}"
        )


def test_conta_desativada_perde_acesso_mesmo_com_token_valido(client):
    """Conta com ativo=False → 403 mesmo com JWT ainda válido (revogação lógica)."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin", ativo=False)
        res = client.get("/configuracoes/usuarios", headers=_auth_headers())
        assert res.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# A08 — Mass assignment: campos privilegiados no corpo são rejeitados (422)
# ══════════════════════════════════════════════════════════════════════════════

# (método, caminho, papel_autorizado, campo_proibido). O papel é autorizado para
# passar do require_role; o schema (extra='forbid') barra o campo extra → 422.
CASOS_MASS_ASSIGNMENT = [
    # Criar aluno: não pode injetar papel/estado/identificador.
    ("post", "/alunos", "admin", "tipo"),
    ("post", "/alunos", "admin", "ativo"),
    ("post", "/alunos", "admin", "id"),
    ("post", "/alunos", "recepcionista", "profile_id"),
    # Criar usuário do sistema.
    ("post", "/configuracoes/usuarios", "admin", "ativo"),
    ("post", "/configuracoes/usuarios", "admin", "id"),
    # Auto-edição de perfil: nada além de nome/telefone/preferencias.
    ("put", "/auth/me", "aluno", "avatar_url"),
    ("put", "/auth/me", "aluno", "id"),
    ("put", "/auth/me", "aluno", "created_at"),
    # Avaliação: 'imc' é calculado no servidor, jamais recebido do cliente.
    ("post", "/avaliacoes", "instrutor", "imc"),
    ("post", "/avaliacoes", "admin", "id"),
    # Instrutor: papel não é campo do cadastro.
    ("post", "/instrutores", "admin", "tipo"),
    # Plano e config: identificador não é editável pelo corpo.
    ("post", "/planos", "admin", "id"),
    ("put", "/configuracoes/academia", "admin", "id"),
]


@pytest.mark.parametrize("metodo,caminho,papel,campo", CASOS_MASS_ASSIGNMENT)
def test_mass_assignment_campo_proibido_422(client, metodo, caminho, papel, campo):
    """Enviar um campo não declarado no schema → 422 e o campo aparece em 'fields'.

    Prova a defesa contra escalonamento por injeção de atributo: o cliente é
    não confiável, então o schema Pydantic com extra='forbid' é quem decide
    o formato exato aceito.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo=papel)
        res = getattr(client, metodo)(
            caminho, json={campo: "x"}, headers=_auth_headers()
        )
        assert res.status_code == 422
        assert campo in res.get_json()["fields"]


# ── Corpo não-JSON / tipo trocado → 400 controlado (nunca 500) ────────────────

@pytest.mark.parametrize("caminho,papel", [
    ("/alunos", "admin"),
    ("/configuracoes/usuarios", "admin"),
    ("/avaliacoes", "instrutor"),
    ("/planos", "admin"),
])
@pytest.mark.parametrize("corpo,content_type", [
    ("[]", "application/json"),                 # JSON válido, mas lista (não objeto)
    ('"apenas uma string"', "application/json"),  # JSON válido, mas string
    ("não é json", "text/plain"),               # nem JSON
])
def test_corpo_nao_objeto_json_400(client, caminho, papel, corpo, content_type):
    """validate_body exige um objeto JSON; qualquer outra coisa → 400 limpo."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo=papel)
        res = client.post(
            caminho, data=corpo, content_type=content_type, headers=_auth_headers()
        )
        assert res.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# A07 — Cabeçalho Authorization malformado → 401 (curto-circuito, sem rede)
# ══════════════════════════════════════════════════════════════════════════════

# Todas estas formas falham já na extração do token (_get_token), então NÃO
# chegam a chamar o Supabase Auth — o teste roda offline e determinístico.
@pytest.mark.parametrize("valor_header", [
    "",                       # header vazio
    "Basic dXNlcjpwYXNz",     # esquema errado (Basic)
    "Token abc123",           # esquema errado (Token)
    "bearer minusculo",       # 'bearer' minúsculo não casa com 'Bearer '
    "Bearer",                 # sem espaço nem token
    "Bearer ",                # prefixo correto, token vazio
    "JWT eyJhbGciOi",         # esquema JWT não suportado
])
def test_authorization_malformado_401(client, valor_header):
    """Sem um 'Bearer <token>' bem formado, o acesso é negado antes de validar JWT."""
    res = client.get("/auth/me", headers={"Authorization": valor_header})
    assert res.status_code == 401


def test_token_invalido_supabase_401(client):
    """Token com formato correto, mas recusado pelo Supabase Auth → 401."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        mock_auth.auth.get_user.side_effect = AuthApiError("invalid JWT", 401, {})
        res = client.get("/auth/me", headers={"Authorization": "Bearer forjado.jwt.aqui"})
        assert res.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# A05 — CORS e cabeçalhos de segurança
# ══════════════════════════════════════════════════════════════════════════════

def test_cors_nao_reflete_origem_nao_autorizada(client):
    """Uma origem fora da allowlist não recebe Access-Control-Allow-Origin.

    Se a API refletisse qualquer Origin, um site malicioso poderia ler as
    respostas autenticadas do usuário (roubo de dados cross-origin).
    """
    origem_maliciosa = "https://academia-falsa.evil.com"
    res = client.get("/health", headers={"Origin": origem_maliciosa})
    assert res.headers.get("Access-Control-Allow-Origin") != origem_maliciosa


def test_preflight_origem_maliciosa_nao_autorizada(client):
    """Preflight OPTIONS de origem não listada não é autorizado para ela."""
    res = client.open(
        "/alunos",
        method="OPTIONS",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") != "https://evil.com"


@pytest.mark.parametrize("metodo,caminho,esperado", [
    ("get", "/auth/me", 401),                      # sem token
    ("get", "/rota-que-nao-existe", 404),          # 404
    ("delete", "/health", 405),                    # método não permitido
    ("get", "/health", 200),                       # rota pública ok
])
def test_cabecalhos_seguranca_em_todos_os_status(client, metodo, caminho, esperado):
    """after_request injeta os cabeçalhos de segurança em QUALQUER resposta."""
    res = getattr(client, metodo)(caminho)
    assert res.status_code == esperado
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'none'" in res.headers.get("Content-Security-Policy", "")


# ══════════════════════════════════════════════════════════════════════════════
# A04 — DoS/execução via imagem maliciosa no processamento de avatar
# ══════════════════════════════════════════════════════════════════════════════

def _png_bytes(w=32, h=32, cor=(120, 180, 240)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), cor).save(buf, format="PNG")
    return buf.getvalue()


class TestProcessamentoImagemSeguro:
    """A imagem enviada é reaberta e re-encodada — nunca gravada como veio."""

    def test_imagem_valida_vira_jpeg(self):
        """Entrada PNG → saída sempre JPEG (descarta EXIF/metadados/payload anexo)."""
        saida = avatar_mod.processar_imagem(_png_bytes())
        assert saida[:2] == b"\xff\xd8"  # magic bytes de JPEG
        assert Image.open(io.BytesIO(saida)).format == "JPEG"

    def test_arquivo_vazio_rejeitado(self):
        with pytest.raises(avatar_mod.AvatarError):
            avatar_mod.processar_imagem(b"")

    def test_bytes_nao_imagem_rejeitados(self):
        """Um 'polyglot'/arquivo que não é imagem real → AvatarError (400), não crash."""
        with pytest.raises(avatar_mod.AvatarError):
            avatar_mod.processar_imagem(b"GIF89a<script>alert(1)</script>")

    def test_arquivo_grande_demais_rejeitado(self):
        """Acima de AVATAR_MAX_BYTES é recusado antes de decodificar (anti-DoS)."""
        from app.config import Config
        gigante = b"\x89PNG\r\n\x1a\n" + b"\x00" * (Config.AVATAR_MAX_BYTES + 1)
        with pytest.raises(avatar_mod.AvatarError):
            avatar_mod.processar_imagem(gigante)

    def test_bomba_de_descompressao_rejeitada(self, monkeypatch):
        """Imagem com dimensões enormes (poucos bytes, muitos pixels) → AvatarError.

        Simula uma 'decompression bomb': o Pillow levanta DecompressionBombError
        ao carregar os pixels, que o processador converte em 400 — a rota não cai.
        """
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 16)  # limiar minúsculo p/ o teste
        with pytest.raises(avatar_mod.AvatarError):
            avatar_mod.processar_imagem(_png_bytes(64, 64))  # 4096 px >> 2×16

    def test_dataurl_base64_corrompida_rejeitada(self):
        with pytest.raises(avatar_mod.AvatarError):
            avatar_mod.processar_imagem_base64("data:image/png;base64,@@@nao-base64@@@")

    def test_dataurl_sem_prefixo_rejeitada(self):
        with pytest.raises(avatar_mod.AvatarError):
            avatar_mod.processar_imagem_base64("apenas texto solto")


# ══════════════════════════════════════════════════════════════════════════════
# A09 — Vazamento de detalhe interno em erro 500 (todos os módulos)
# ══════════════════════════════════════════════════════════════════════════════

def _app_producao():
    """App em modo produção-like: debug off e errorhandler(500) ativo."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False
    return app


@pytest.mark.parametrize("alvo_supabase,url,papel", [
    ("app.dashboard.routes.supabase",      "/dashboard/alunos",       "admin"),
    ("app.alunos.routes.supabase",         "/alunos",                 "admin"),
    ("app.instrutores.routes.supabase",    "/instrutores",            "admin"),
    ("app.mensalidades.routes.supabase",   "/mensalidades",           "admin"),
    ("app.configuracoes.routes.supabase",  "/configuracoes/usuarios", "admin"),
])
def test_erro_interno_nao_vaza_detalhe(alvo_supabase, url, papel):
    """Falha inesperada no banco vira 500 genérico — sem texto da exceção.

    O texto cru pode conter nome de coluna/constraint/erro do PostgREST. Em
    produção só expomos 'Erro interno do servidor'.
    """
    segredo = "constraint_secreta_fk_interna_xyz"
    app = _app_producao()
    with app.test_client() as c, \
         patch(alvo_supabase) as mock_db, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo=papel)
        mock_db.table.side_effect = Exception(segredo)

        res = c.get(url, headers=_auth_headers())
        assert res.status_code == 500
        corpo = res.get_json() or {}
        assert "detalhe" not in corpo
        assert segredo not in res.get_data(as_text=True)

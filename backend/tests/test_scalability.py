"""Testes de escalabilidade e limites — as barreiras que seguram o sistema
conforme a base de alunos/mensalidades cresce.

Não medem performance (isso é papel de load test), mas travam as decisões de
projeto que evitam degradação e DoS quando o volume aumenta:

  Paginação obrigatória (server-side)
    A listagem de alunos NUNCA busca a tabela inteira: aplica range(offset, ...)
    e count='exact'. Com 10 mil alunos, sem paginação, cada request arrastaria
    tudo para a memória. O `limit` é restrito a uma allowlist (25/50/100/200)
    para o cliente não pedir uma página gigante.

  Entrada limitada (anti-DoS)
    - Corpo da requisição tem teto (MAX_CONTENT_LENGTH) → 413 antes de ler.
    - Foto (data URL) tem teto de tamanho no schema, antes de decodificar base64.

  Rate limit configurável e compartilhável
    Os limites vêm de env (Config.RATELIMIT_*) e a chave separa por sessão/IP,
    para o controle continuar válido quando houver vários workers/instâncias.

Estes testes documentam os pontos que precisarão de índice/cache/redis quando
o volume subir — se algum for afrouxado sem querer, o teste avisa.
"""
from unittest.mock import patch, MagicMock

import pytest

from app import create_app
from app.config import Config
from app.extensions import rate_limit_key
from tests._helpers import (
    mock_auth as _mock_auth,
    auth_headers as _auth_headers,
    self_chain as _self_chain,
)


# ══════════════════════════════════════════════════════════════════════════════
# Paginação server-side na listagem de alunos
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("limit_pedido,limit_efetivo", [
    (25, 25),          # valor da allowlist é respeitado
    (200, 200),        # maior valor permitido
    (99999, 50),       # acima do teto → cai no padrão seguro (50)
    (10, 50),          # fora da allowlist → padrão
    ("abc", 50),       # não numérico → padrão (sem 500)
    (-5, 50),          # negativo → padrão
])
def test_alunos_limit_restrito_a_allowlist(client, limit_pedido, limit_efetivo):
    """O cliente não escolhe uma página arbitrariamente grande.

    Sem essa trava, ?limit=1000000 arrastaria a tabela inteira por request.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        chain = _self_chain(MagicMock(data=[], count=0))
        mock_supa.table.return_value = chain

        res = client.get(
            "/alunos", query_string={"limit": limit_pedido}, headers=_auth_headers()
        )
        assert res.status_code == 200
        assert res.get_json()["limit"] == limit_efetivo


@pytest.mark.parametrize("offset_pedido,offset_efetivo", [
    (0, 0),
    (100, 100),
    (-10, 0),          # negativo é normalizado para 0
    ("xyz", 0),        # não numérico → 0 (sem 500)
])
def test_alunos_offset_normalizado(client, offset_pedido, offset_efetivo):
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        chain = _self_chain(MagicMock(data=[], count=0))
        mock_supa.table.return_value = chain

        res = client.get(
            "/alunos", query_string={"offset": offset_pedido}, headers=_auth_headers()
        )
        assert res.status_code == 200
        assert res.get_json()["offset"] == offset_efetivo


def test_alunos_lista_sempre_pagina_no_banco(client):
    """A query aplica range() e count='exact' — nunca traz a tabela inteira.

    Prova que a paginação acontece no Postgres (uma página por vez), não em
    memória no Python. É o que mantém o endpoint barato com a base crescendo.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        chain = _self_chain(MagicMock(data=[], count=0))
        mock_supa.table.return_value = chain

        res = client.get("/alunos", query_string={"limit": 25}, headers=_auth_headers())
        assert res.status_code == 200
        # range(offset, offset+limit-1) → página no servidor.
        assert chain.range.called
        assert chain.range.call_args.args == (0, 24)
        # count='exact' → total sem trazer todas as linhas.
        _, kwargs = mock_supa.table.return_value.select.call_args
        assert kwargs.get("count") == "exact"


# ══════════════════════════════════════════════════════════════════════════════
# Entrada limitada — anti-DoS por corpo/imagem gigante
# ══════════════════════════════════════════════════════════════════════════════

def test_max_content_length_configurado(client):
    """Há um teto global de corpo da requisição (barra upload gigante cedo)."""
    limite = client.application.config.get("MAX_CONTENT_LENGTH")
    assert limite is not None
    # Teto = tamanho máx. de avatar + folga de 1 MB para overhead do multipart.
    assert limite == Config.AVATAR_MAX_BYTES + 1024 * 1024


def test_corpo_acima_do_teto_retorna_413(client):
    """Corpo maior que MAX_CONTENT_LENGTH → 413, sem ler tudo na memória."""
    limite = client.application.config["MAX_CONTENT_LENGTH"]
    corpo_gigante = b"x" * (limite + 1)
    res = client.post(
        "/auth/login",
        data=corpo_gigante,
        content_type="application/json",
    )
    assert res.status_code == 413


def test_foto_dataurl_gigante_rejeitada_pelo_schema():
    """A foto (data URL base64) tem teto de tamanho ANTES de decodificar base64.

    Sem isso, um cliente poderia mandar dezenas de MB de base64 e forçar o
    servidor a decodificar/processar antes de recusar.
    """
    from pydantic import ValidationError
    from app.schemas import AlunoCreateSchema, _FOTO_MAX_LEN

    foto_gigante = "data:image/png;base64," + "A" * (_FOTO_MAX_LEN + 1)
    with pytest.raises(ValidationError):
        AlunoCreateSchema(
            nome="Fulano", email="a@a.com", senha="senha123", cpf="12345678901",
            foto=foto_gigante,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Rate limit — configurável por env e com chave que escala entre workers
# ══════════════════════════════════════════════════════════════════════════════

def test_rate_limit_login_configuravel_por_env():
    """Os limites vêm de env — dá para endurecer em produção sem mudar código."""
    assert Config.RATELIMIT_LOGIN
    assert Config.RATELIMIT_DEFAULT


def test_rate_limit_key_separa_por_sessao_e_ip():
    """Autenticado → balde por token; anônimo → balde por IP.

    Separar por sessão evita que um usuário legítimo esgote a cota compartilhada
    de outro; para endpoints públicos (login) cai no IP, que é o certo ali.
    """
    app = create_app()
    app.config["TESTING"] = True

    with app.test_request_context(headers={"Authorization": "Bearer sessao-abc"}):
        assert rate_limit_key() == "Bearer sessao-abc"

    with app.test_request_context(environ_base={"REMOTE_ADDR": "203.0.113.9"}):
        assert rate_limit_key() == "203.0.113.9"


def test_storage_uri_de_rate_limit_tem_default():
    """Há um storage configurável; em produção deve virar redis:// (compartilhado).

    Com 'memory://' o limite não é compartilhado entre workers — este teste
    documenta o ponto que precisa de Redis quando escalar horizontalmente.
    """
    assert Config.RATELIMIT_STORAGE_URI

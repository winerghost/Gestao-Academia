import logging

import httpx
from supabase import create_client, Client
from supabase.client import ClientOptions
from .config import Config

logger = logging.getLogger(__name__)

# Número de novas tentativas para erros de conexão transitórios.
_MAX_RETRIES = 2


class _RetryTransport(httpx.HTTPTransport):
    """Transporte HTTP que repete a requisição em desconexões transitórias.

    O Supabase fica atrás do Cloudflare, que encerra silenciosamente conexões
    ociosas. Como o cliente global do Flask mantém um pool de conexões vivo
    entre requisições, a próxima query pode reaproveitar um socket já morto e
    falhar com ``RemoteProtocolError: Server disconnected`` (retornando 500).

    Aqui repetimos a requisição quando isso ocorre. Só erros de conexão
    (antes de qualquer resposta do servidor) são repetidos, então é seguro
    mesmo para requisições não idempotentes: se o servidor desconectou, ele
    não chegou a processar nada.
    """

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        last_exc: Exception | None = None
        for tentativa in range(_MAX_RETRIES + 1):
            try:
                return super().handle_request(request)
            except (httpx.RemoteProtocolError, httpx.ConnectError) as exc:
                last_exc = exc
                logger.warning(
                    "Conexão com o Supabase caiu (%s) — tentativa %d/%d",
                    type(exc).__name__,
                    tentativa + 1,
                    _MAX_RETRIES + 1,
                )
        raise last_exc  # type: ignore[misc]


def _harden_session(client: Client) -> Client:
    """Troca a sessão httpx do PostgREST por uma resiliente a desconexões.

    Duas mudanças sobre o padrão da lib ``postgrest``:
    - ``http2=False``: o multiplexing HTTP/2 com o Cloudflare é a principal
      causa do ``Server disconnected`` intermitente; o HTTP/1.1 com keep-alive
      é mais estável aqui.
    - transporte com retry (``_RetryTransport``) para cobrir o caso em que a
      conexão é fechada mesmo assim.

    Preserva base_url, headers (apikey/Authorization), timeout e auth da
    sessão original criada pela lib.
    """
    old = client.postgrest.session
    new = httpx.Client(
        base_url=old.base_url,
        headers=old.headers,
        timeout=old.timeout,
        follow_redirects=True,
        http2=False,
        transport=_RetryTransport(http2=False),
    )
    new.auth = old.auth
    old.close()
    client.postgrest.session = new
    return client

# ── Separação de responsabilidades ────────────────────────────────────────────
# O frontend (Next.js) usa o SDK Supabase APENAS para gerenciar sessão local
# (getSession / setSession / signOut). Toda lógica de dados passa por aqui.
#
# Cliente administrativo (service role) — bypassa RLS.
# Use APENAS para operações de backend: queries de dados e a Admin API
# de auth (create_user, sign_out, etc.).
#
# ATENÇÃO: nunca use este cliente para login de usuário. Ele é global e
# compartilhado entre todas as requisições do Flask; `sign_in_with_password`
# grava a sessão no cliente, o que (a) vaza a identidade de um usuário para
# requisições de outros e (b) troca o header de autorização do PostgREST do
# service role para o JWT do usuário, quebrando as operações administrativas.
supabase: Client = _harden_session(
    create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
)


def get_anon_client() -> Client:
    """Retorna um cliente novo e isolado, com a chave ANON e sem estado.

    Cada chamada cria uma instância própria que não persiste sessão nem faz
    refresh automático de token. Use para operações de autenticação por
    requisição (ex.: login), garantindo que a sessão do usuário nunca toque
    o cliente global de service role.
    """
    options = ClientOptions(persist_session=False, auto_refresh_token=False)
    return _harden_session(
        create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY, options)
    )


def get_user_client(token: str) -> Client:
    """Cliente sob a identidade do usuário (chave ANON + JWT do usuário).

    As requisições ao PostgREST viajam com o access token do usuário, então
    as RLS policies do banco são aplicadas como aquele usuário. Use para
    leituras/escritas que devem respeitar ownership (mitiga BOLA/IDOR): o
    banco, e não a aplicação, decide quais linhas o usuário pode ver.
    """
    client = get_anon_client()
    # Define o Bearer do usuário nas chamadas do PostgREST → RLS ativa.
    client.postgrest.auth(token)
    return client

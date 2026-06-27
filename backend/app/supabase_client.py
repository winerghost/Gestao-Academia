from supabase import create_client, Client
from supabase.client import ClientOptions
from .config import Config

# Cliente administrativo (service role) — bypassa RLS.
# Use APENAS para operações de backend: queries de dados e a Admin API
# de auth (create_user, sign_out, etc.).
#
# ATENÇÃO: nunca use este cliente para login de usuário. Ele é global e
# compartilhado entre todas as requisições do Flask; `sign_in_with_password`
# grava a sessão no cliente, o que (a) vaza a identidade de um usuário para
# requisições de outros e (b) troca o header de autorização do PostgREST do
# service role para o JWT do usuário, quebrando as operações administrativas.
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)


def get_anon_client() -> Client:
    """Retorna um cliente novo e isolado, com a chave ANON e sem estado.

    Cada chamada cria uma instância própria que não persiste sessão nem faz
    refresh automático de token. Use para operações de autenticação por
    requisição (ex.: login), garantindo que a sessão do usuário nunca toque
    o cliente global de service role.
    """
    options = ClientOptions(persist_session=False, auto_refresh_token=False)
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY, options)


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

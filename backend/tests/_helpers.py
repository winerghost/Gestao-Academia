"""Helpers de teste compartilhados — mocks de autenticação robustos.

Centraliza o que antes era duplicado (e divergente) no topo de cada arquivo de
teste: cada um tinha sua própria cópia de `_mock_auth`, algumas mockando só
`.single()`, outras só `.maybe_single()`, com `ativo`/`id` inconsistentes. Isso
é frágil — um teste podia passar por acidente (ou mascarar um 401/403 real)
dependendo de qual finalizador o middleware chamasse.

Ponto único de verdade: se o middleware de auth mudar, ajusta-se só aqui.
"""
from unittest.mock import MagicMock

# UUIDs válidos para path params <uuid:...> (Flask 404 antes do handler se inválido).
UUID_A = "00000000-0000-0000-0000-00000000000a"
UUID_B = "00000000-0000-0000-0000-00000000000b"

_TOKEN_FAKE = "token-fake"


def auth_headers(token=_TOKEN_FAKE):
    """Header Authorization no formato que o middleware aceita ('Bearer <token>')."""
    return {"Authorization": f"Bearer {token}"}


def mock_auth(mock_supa, tipo="admin", user_id="user-uuid", ativo=True):
    """Configura o supabase do middleware para simular um usuário logado.

    Robusto de propósito:
      - mocka os DOIS finalizadores de query (.single e .maybe_single), então o
        teste não quebra se o middleware trocar um pelo outro;
      - inclui 'ativo' no profile, refletindo o gate de conta desativada
        (require_auth devolve 403 quando ativo=False, mesmo com token válido).

    Passe ativo=False para exercitar o caminho de conta desativada.
    Retorna o mock do profile, caso o teste queira inspecioná-lo.
    """
    user = MagicMock()
    user.id = user_id
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    perfil = MagicMock(data={"id": user_id, "tipo": tipo, "ativo": ativo})
    eq = mock_supa.table.return_value.select.return_value.eq.return_value
    eq.single.return_value.execute.return_value = perfil
    eq.maybe_single.return_value.execute.return_value = perfil
    return perfil


def self_chain(execute_result):
    """Mock 'auto-retornante': cada método do query builder devolve a própria cadeia.

    Útil para handlers que aplicam filtros variáveis (busca/datas/paginação):
    sem isso, o teste teria que prever a ordem exata dos métodos encadeados.
    """
    chain = MagicMock()
    for metodo in (
        "select", "eq", "neq", "ilike", "filter", "order", "range", "in_",
        "gte", "lte", "or_", "single", "maybe_single", "limit", "insert", "update",
    ):
        getattr(chain, metodo).return_value = chain
    chain.execute.return_value = execute_result
    return chain

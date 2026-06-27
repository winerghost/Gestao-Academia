"""Testes do transporte resiliente do cliente Supabase.

Cobre o bug de ``RemoteProtocolError: Server disconnected`` que ocorria quando
o pool de conexões HTTP/2 reaproveitava um socket já fechado pelo Cloudflare.
"""
from unittest.mock import patch

import httpx
import pytest

from app.supabase_client import _RetryTransport, _MAX_RETRIES


def _req():
    return httpx.Request("GET", "https://x.supabase.co/rest/v1/profiles")


def test_retry_recupera_apos_desconexao_transitoria():
    """Falha algumas vezes e depois responde -> deve retornar a resposta."""
    chamadas = {"n": 0}

    def fake(self, request):
        chamadas["n"] += 1
        if chamadas["n"] <= _MAX_RETRIES:
            raise httpx.RemoteProtocolError("Server disconnected")
        return httpx.Response(200, request=request)

    with patch.object(httpx.HTTPTransport, "handle_request", fake):
        resp = _RetryTransport(http2=False).handle_request(_req())

    assert resp.status_code == 200
    assert chamadas["n"] == _MAX_RETRIES + 1


def test_retry_desiste_e_relanca_apos_esgotar_tentativas():
    """Falha sempre -> relança o erro após _MAX_RETRIES + 1 tentativas."""
    chamadas = {"n": 0}

    def fake(self, request):
        chamadas["n"] += 1
        raise httpx.RemoteProtocolError("Server disconnected")

    with patch.object(httpx.HTTPTransport, "handle_request", fake):
        with pytest.raises(httpx.RemoteProtocolError):
            _RetryTransport(http2=False).handle_request(_req())

    assert chamadas["n"] == _MAX_RETRIES + 1


def test_retry_nao_repete_erro_nao_transitorio():
    """Erros que não são de conexão não devem ser repetidos."""
    chamadas = {"n": 0}

    def fake(self, request):
        chamadas["n"] += 1
        raise httpx.ReadTimeout("timeout")

    with patch.object(httpx.HTTPTransport, "handle_request", fake):
        with pytest.raises(httpx.ReadTimeout):
            _RetryTransport(http2=False).handle_request(_req())

    assert chamadas["n"] == 1

"""HTTP-клиент к hosted-бэкенду: happy path, 4xx/5xx, таймаут (respx-моки)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from mcp_pharma.client import PharmaClient
from mcp_pharma.config import Settings
from mcp_pharma.errors import BackendError, BackendUnavailable

BASE = "http://test/pharma"


def _client() -> PharmaClient:
    return PharmaClient(Settings(api_base=BASE, token="k", timeout=5.0))


@respx.mock
async def test_registration_happy_path() -> None:
    respx.post(f"{BASE}/v1/registration").mock(
        return_value=httpx.Response(
            200,
            json={"status": "active", "ru_number": "ЛП-001234", "source": "grls"},
        )
    )
    c = _client()
    try:
        out = await c.check_registration("Панадол", None, None)
        assert out["status"] == "active"
        assert out["source"] == "grls"
    finally:
        await c.aclose()


@respx.mock
async def test_search_happy_path() -> None:
    respx.post(f"{BASE}/v1/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"name_trade": "Панадол", "mnn": "парацетамол"}], "source": "grls"},
        )
    )
    c = _client()
    try:
        out = await c.search("парацетамол", 20)
        assert out["results"][0]["mnn"] == "парацетамол"
        assert out["source"] == "grls"
    finally:
        await c.aclose()


@respx.mock
async def test_zhnvlp_sends_mnn() -> None:
    route = respx.post(f"{BASE}/v1/zhnvlp").mock(
        return_value=httpx.Response(200, json={"in_zhnvlp": True, "price_limit_rub": "123.45"})
    )
    c = _client()
    try:
        out = await c.zhnvlp_price(None, "омепразол")
        assert out["in_zhnvlp"] is True
        sent = json.loads(route.calls.last.request.read())
        assert sent == {"name": None, "mnn": "омепразол"}
    finally:
        await c.aclose()


@respx.mock
async def test_backend_401() -> None:
    respx.post(f"{BASE}/v1/card").mock(return_value=httpx.Response(401, json={"error": "unauthorized"}))
    c = _client()
    try:
        with pytest.raises(BackendError) as ei:
            await c.get_card("Панадол", None)
        assert ei.value.status_code == 401
    finally:
        await c.aclose()


@respx.mock
async def test_backend_500() -> None:
    respx.post(f"{BASE}/v1/recall").mock(return_value=httpx.Response(500, text="boom"))
    c = _client()
    try:
        with pytest.raises(BackendError) as ei:
            await c.check_recall("Панадол", None)
        assert ei.value.status_code == 500
    finally:
        await c.aclose()


@respx.mock
async def test_timeout() -> None:
    respx.post(f"{BASE}/v1/instruction").mock(side_effect=httpx.TimeoutException("slow"))
    c = _client()
    try:
        with pytest.raises(BackendUnavailable):
            await c.get_instruction("Панадол", None)
    finally:
        await c.aclose()

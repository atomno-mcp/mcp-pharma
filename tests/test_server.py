"""Серверный слой: hosted wrappers, validation, tool paths, client singleton."""

from __future__ import annotations

from dataclasses import replace

import pytest

import mcp_pharma.server as srv
from mcp_pharma.errors import BackendError, PharmaError


async def test_no_token_hint(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token=None))
    out = await srv._hosted_call("x", lambda: _fail())
    assert out["error"] == "missing_token"
    assert "MCP_PHARMA_API_KEY" in out["message_ru"]
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_disclaimer_injected(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _ok() -> dict:
        return {"results": []}

    out = await srv._hosted_call("x", _ok)
    assert out["disclaimer"] == srv.DISCLAIMER


def test_invalid_input_carries_disclaimer() -> None:
    out = srv._invalid_input("Укажите name или mnn.")
    assert out["error"] == "invalid_input"
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_hosted_backend_error_500(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _boom() -> dict:
        raise BackendError(500, "down")

    out = await srv._hosted_call("search_drug", _boom)
    assert out["error"] == "backend_error"


async def test_hosted_backend_error_401(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _boom() -> dict:
        raise BackendError(401, "bad")

    out = await srv._hosted_call("search_drug", _boom)
    assert out["error"] == "missing_token"


async def test_hosted_pharma_error(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _boom() -> dict:
        raise PharmaError("offline")

    out = await srv._hosted_call("search_drug", _boom)
    assert out["error"] == "unavailable"


@pytest.fixture
def with_token_and_mock_call(monkeypatch):
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _mock_call(fn):
        return {"ok": True}

    monkeypatch.setattr(srv, "_call", _mock_call)


async def test_check_drug_registration_validation() -> None:
    out = await srv.check_drug_registration()
    assert out["error"] == "invalid_input"


async def test_check_drug_registration_tool(with_token_and_mock_call) -> None:
    out = await srv.check_drug_registration(name="Панадол")
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_get_drug_card_validation() -> None:
    out = await srv.get_drug_card()
    assert out["error"] == "invalid_input"


async def test_get_drug_card_tool(with_token_and_mock_call) -> None:
    out = await srv.get_drug_card(name="Панадол")
    assert out["ok"] is True


async def test_search_drug_tool(with_token_and_mock_call) -> None:
    out = await srv.search_drug("парацетамол", 10)
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_get_zhnvlp_price_validation() -> None:
    out = await srv.get_zhnvlp_price()
    assert out["error"] == "invalid_input"


async def test_get_zhnvlp_price_tool(with_token_and_mock_call) -> None:
    out = await srv.get_zhnvlp_price(mnn="парацетамол")
    assert out["ok"] is True


async def test_check_recall_validation() -> None:
    out = await srv.check_recall()
    assert out["error"] == "invalid_input"


async def test_check_recall_tool(with_token_and_mock_call) -> None:
    out = await srv.check_recall(name="Панадол", series="A1")
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_get_instruction_validation() -> None:
    out = await srv.get_instruction()
    assert out["error"] == "invalid_input"


async def test_get_instruction_tool(with_token_and_mock_call) -> None:
    out = await srv.get_instruction(ru_number="ЛП-001234")
    assert out["ok"] is True


async def test_get_client_singleton(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_client", None)
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k", api_base="http://test"))

    class FakeClient:
        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(srv, "PharmaClient", lambda _s: FakeClient())
    first = await srv._get_client()
    second = await srv._get_client()
    assert first is second


def test_build_arg_parser_version() -> None:
    parser = srv._build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])


async def _fail() -> dict:
    raise AssertionError("should not be called without token")

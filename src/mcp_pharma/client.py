"""HTTP-клиент к hosted-бэкенду pharma (api.atomno-mcp.ru/pharma).

Тонкая обёртка над httpx: один общий AsyncClient, заголовок X-API-Key, маппинг
ошибок в PharmaError. Никакой бизнес-логики (парсинг ГРЛС/ЖНВЛП, нормализация
МНН↔ТН и доступ к реестрам — на приватном сервере). ПДн пациентов на нашей
стороне нет — это справочник препаратов.
"""

from __future__ import annotations

from typing import Any

import httpx

from . import __version__
from .config import Settings
from .errors import BackendError, BackendUnavailable

_USER_AGENT = f"atomno-mcp-pharma/{__version__}"


class PharmaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
        if settings.token:
            headers["X-API-Key"] = settings.token
        self._client = httpx.AsyncClient(
            base_url=settings.api_base,
            timeout=settings.timeout,
            headers=headers,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = await self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise BackendUnavailable(f"timeout calling {path}") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailable(f"network error calling {path}: {exc}") from exc
        return self._parse(resp)

    @staticmethod
    def _parse(resp: httpx.Response) -> dict[str, Any]:
        if resp.status_code >= 400:
            raise BackendError(resp.status_code, _extract_detail(resp))
        try:
            return resp.json()
        except ValueError as exc:
            raise BackendError(resp.status_code, "invalid JSON in response") from exc

    async def check_registration(
        self,
        name: str | None,
        mnn: str | None,
        ru_number: str | None,
    ) -> dict[str, Any]:
        return await self._post(
            "/v1/registration",
            {"name": name, "mnn": mnn, "ru_number": ru_number},
        )

    async def get_card(self, name: str | None, ru_number: str | None) -> dict[str, Any]:
        return await self._post("/v1/card", {"name": name, "ru_number": ru_number})

    async def search(self, query: str, limit: int) -> dict[str, Any]:
        return await self._post("/v1/search", {"query": query, "limit": limit})

    async def zhnvlp_price(self, name: str | None, mnn: str | None) -> dict[str, Any]:
        return await self._post("/v1/zhnvlp", {"name": name, "mnn": mnn})

    async def check_recall(self, name: str | None, series: str | None) -> dict[str, Any]:
        return await self._post("/v1/recall", {"name": name, "series": series})

    async def get_instruction(
        self, name: str | None, ru_number: str | None
    ) -> dict[str, Any]:
        return await self._post("/v1/instruction", {"name": name, "ru_number": ru_number})


def _extract_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:300] or resp.reason_phrase
    if isinstance(body, dict):
        for key in ("message_ru", "detail", "message", "error"):
            if body.get(key):
                return str(body[key])
    return str(body)[:300]

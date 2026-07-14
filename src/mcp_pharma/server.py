"""FastMCP entrypoint для atomno-mcp-pharma (тонкий клиент).

Все тулы проксируют к hosted-бэкенду Atomno Labs (тариф Pro, ключ
MCP_PHARMA_API_KEY): check_drug_registration, get_drug_card, search_drug,
get_zhnvlp_price, check_recall, get_instruction. Каждый ответ несёт
disclaimer/source.

Это справочная выдача государственных реестров ГРЛС/ЖНВЛП. Тулы НЕ формируют
показаний, дозировок-назначений, оценок взаимодействий и подбора замен — это
инвариант продукта (см. spec, разделы 4.4 и 8), а не опция.
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import logging
import os
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from . import __version__
from .client import PharmaClient
from .config import Settings
from .errors import BackendError, PharmaError

logger = logging.getLogger("mcp_pharma")

_SUPPORTED_TRANSPORTS = ("stdio", "http", "sse", "streamable-http")
_DEFAULT_TRANSPORT = "stdio"
_DEFAULT_HTTP_HOST = "127.0.0.1"
_DEFAULT_HTTP_PORT = 8000
_VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

DISCLAIMER = (
    "Справочная информация из государственных реестров ГРЛС/ЖНВЛП (Минздрав РФ). "
    "Не является медицинской консультацией, назначением или рекомендацией. "
    "По вопросам применения, дозировки, показаний и совместимости препаратов "
    "обратитесь к врачу или фармацевту."
)

mcp: FastMCP = FastMCP(
    name="atomno-mcp-pharma",
    instructions=(
        "Russian drug reference for AI agents: query the state registers ГРЛС "
        "(drug registration) and ЖНВЛП (vital-and-essential drugs list with "
        "state-capped prices). Check registration status by trade name, INN "
        "(МНН) or registration-certificate number (РУ); get a full drug card "
        "(forms, dosages, holder, manufacturer, ATC); look up ЖНВЛП inclusion "
        "and the registered price cap; check Roszdravnadzor recalls; and get a "
        "link to the official instruction. All tools go through the Atomno Labs "
        "hosted API and need a Pro key (MCP_PHARMA_API_KEY). This is a reference "
        "lookup of open government data, NOT medical advice: it does not provide "
        "indications, dosing, interactions or substitutions. Every answer carries "
        "a disclaimer and a source. Get a key at "
        "https://atomno-mcp.ru/pricing#pharma-pro."
    ),
)

_client: PharmaClient | None = None
_client_lock = asyncio.Lock()
_settings = Settings.from_env()


async def _get_client() -> PharmaClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is None:
            _client = PharmaClient(_settings)
            atexit.register(_close_client_atexit)
    assert _client is not None
    return _client


def _close_client_atexit() -> None:
    if _client is None:
        return
    try:
        asyncio.run(_client.aclose())
    except RuntimeError:
        pass


def _no_token_hint() -> dict[str, Any]:
    return {
        "error": "missing_token",
        "message_ru": (
            "Не задан MCP_PHARMA_API_KEY. Доступ к актуальным данным ГРЛС/ЖНВЛП "
            "— платный (тариф Pro). Ключ: https://atomno-mcp.ru/pricing#pharma-pro"
        ),
        "disclaimer": DISCLAIMER,
    }


def _invalid_input(hint: str) -> dict[str, Any]:
    return {
        "error": "invalid_input",
        "message": "Не заданы параметры поиска.",
        "hint": hint,
        "disclaimer": DISCLAIMER,
    }


async def _hosted_call(name: str, coro_factory) -> dict[str, Any]:
    if not _settings.has_token:
        return _no_token_hint()
    try:
        result = await coro_factory()
        result.setdefault("disclaimer", DISCLAIMER)
        return result
    except BackendError as exc:
        if exc.status_code == 401:
            return _no_token_hint()
        logger.warning("%s backend %s: %s", name, exc.status_code, exc.detail)
        return {"error": "backend_error", "status": exc.status_code, "message": exc.detail}
    except PharmaError as exc:
        logger.warning("%s failed: %s", name, exc)
        return {"error": "unavailable", "message": str(exc)}


async def _call(fn) -> dict[str, Any]:
    client = await _get_client()
    return await fn(client)


@mcp.tool
async def check_drug_registration(
    name: Annotated[str | None, Field(default=None, description="Торговое наименование (напр. «Панадол»).")] = None,
    mnn: Annotated[str | None, Field(default=None, description="Международное непатентованное наименование / МНН (напр. «парацетамол»).")] = None,
    ru_number: Annotated[str | None, Field(default=None, description="Номер регистрационного удостоверения (напр. «ЛП-001234»).")] = None,
) -> dict[str, Any]:
    """Статус регистрации препарата в ГРЛС (действует/отменён/приостановлен), номер и дата РУ. Задайте name, mnn или ru_number. Тариф Pro."""
    if not (name or mnn or ru_number):
        return _invalid_input("Укажите хотя бы одно: name, mnn или ru_number.")
    return await _hosted_call(
        "check_drug_registration",
        lambda: _call(lambda c: c.check_registration(name, mnn, ru_number)),
    )


@mcp.tool
async def get_drug_card(
    name: Annotated[str | None, Field(default=None, description="Торговое наименование препарата.")] = None,
    ru_number: Annotated[str | None, Field(default=None, description="Номер регистрационного удостоверения (РУ).")] = None,
) -> dict[str, Any]:
    """Справочная карточка препарата из ГРЛС: ТН и МНН, формы и дозировки, держатель РУ, производитель, страна, код АТХ, дата регистрации. Тариф Pro."""
    if not (name or ru_number):
        return _invalid_input("Укажите name или ru_number.")
    return await _hosted_call(
        "get_drug_card",
        lambda: _call(lambda c: c.get_card(name, ru_number)),
    )


@mcp.tool
async def search_drug(
    query: Annotated[str, Field(min_length=1, description="Строка поиска по торговому наименованию (ТН) или МНН.")],
    limit: Annotated[int, Field(default=20, ge=1, le=100, description="Максимум результатов.")] = 20,
) -> dict[str, Any]:
    """Fuzzy-поиск препаратов по торговому наименованию и МНН с ранжированием (мостик МНН↔ТН). Тариф Pro."""
    return await _hosted_call(
        "search_drug",
        lambda: _call(lambda c: c.search(query, limit)),
    )


@mcp.tool
async def get_zhnvlp_price(
    name: Annotated[str | None, Field(default=None, description="Торговое наименование препарата.")] = None,
    mnn: Annotated[str | None, Field(default=None, description="МНН (позиция перечня ЖНВЛП).")] = None,
) -> dict[str, Any]:
    """Входит ли препарат в перечень ЖНВЛП и предельная зарегистрированная цена (ПЗЦ) по позициям (форма/дозировка/фасовка). Задайте name или mnn. Тариф Pro."""
    if not (name or mnn):
        return _invalid_input("Укажите name или mnn.")
    return await _hosted_call(
        "get_zhnvlp_price",
        lambda: _call(lambda c: c.zhnvlp_price(name, mnn)),
    )


@mcp.tool
async def check_recall(
    name: Annotated[str | None, Field(default=None, description="Торговое наименование препарата.")] = None,
    series: Annotated[str | None, Field(default=None, description="Номер серии (если известен).")] = None,
) -> dict[str, Any]:
    """Письма Росздравнадзора об изъятии/отзыве препарата или серии: наличие, дата, реквизиты и причина как в документе (без интерпретации). Задайте name или series. Тариф Pro."""
    if not (name or series):
        return _invalid_input("Укажите name или series.")
    return await _hosted_call(
        "check_recall",
        lambda: _call(lambda c: c.check_recall(name, series)),
    )


@mcp.tool
async def get_instruction(
    name: Annotated[str | None, Field(default=None, description="Торговое наименование препарата.")] = None,
    ru_number: Annotated[str | None, Field(default=None, description="Номер регистрационного удостоверения (РУ).")] = None,
) -> dict[str, Any]:
    """Ссылка на официальную инструкцию из ГРЛС (и её текст как госинформация с атрибуцией первоисточника). Задайте name или ru_number. Тариф Pro."""
    if not (name or ru_number):
        return _invalid_input("Укажите name или ru_number.")
    return await _hosted_call(
        "get_instruction",
        lambda: _call(lambda c: c.get_instruction(name, ru_number)),
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atomno-mcp-pharma",
        description=(
            "MCP server: Russian drug reference (ГРЛС registration, ЖНВЛП price "
            "caps, recalls, instructions)."
        ),
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"atomno-mcp-pharma {__version__}",
        help="Show version and exit.",
    )
    parser.add_argument(
        "--transport",
        "-t",
        choices=_SUPPORTED_TRANSPORTS,
        default=_DEFAULT_TRANSPORT,
        help=f"MCP transport (default: {_DEFAULT_TRANSPORT}).",
    )
    parser.add_argument(
        "--host",
        default=_DEFAULT_HTTP_HOST,
        help=f"Host for http transports (default: {_DEFAULT_HTTP_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_HTTP_PORT,
        help=f"Port for http transports (default: {_DEFAULT_HTTP_PORT}).",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        choices=_VALID_LOG_LEVELS,
        default=None,
        help="Logging level; overrides MCP_PHARMA_LOG_LEVEL (default: INFO).",
    )
    return parser


def _resolve_log_level(cli_value: str | None) -> str:
    if cli_value is not None:
        return cli_value
    env_raw = os.environ.get("MCP_PHARMA_LOG_LEVEL")
    if env_raw is None:
        return "INFO"
    env_norm = env_raw.strip().upper()
    if env_norm in _VALID_LOG_LEVELS:
        return env_norm
    raise ValueError(
        f"MCP_PHARMA_LOG_LEVEL={env_raw!r} is invalid. "
        f"Allowed: {', '.join(_VALID_LOG_LEVELS)}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        log_level = _resolve_log_level(args.log_level)
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover

    logging.basicConfig(level=log_level)
    run_kwargs: dict[str, Any] = {"transport": args.transport}
    if args.transport in ("http", "sse", "streamable-http"):
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port
    mcp.run(**run_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

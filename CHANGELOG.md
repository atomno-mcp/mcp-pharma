# Changelog

Все заметные изменения фиксируются здесь. Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [SemVer](https://semver.org/lang/ru/).

## [0.1.0] — 2026-07-04

### Added

- Тонкий MCP-клиент `atomno-mcp-pharma` (open-core: публичный клиент + приватный hosted-сервер).
- 6 тулов через hosted API (тариф Pro): `check_drug_registration`, `get_drug_card`,
  `search_drug`, `get_zhnvlp_price`, `check_recall`, `get_instruction`.
- Мостик МНН↔ТН в поиске; проверка ЖНВЛП и предельной зарегистрированной цены (ПЗЦ).
- Жёсткая граница «не медконсультация»: обязательный дисклеймер в каждом ответе,
  тулы не формируют показаний/дозировок/взаимодействий/замен.
- CLI argparse (`--help/--version/--transport/--host/--port/--log-level`), env `MCP_PHARMA_*`.
- Метаданные для офиц. MCP Registry (`server.json` + workflow OIDC + маркер `mcp-name`), `glama.json`, `Dockerfile`.

<!-- mcp-name: io.github.atomno-mcp/mcp-pharma -->

# atomno-mcp-pharma

Клиент справочника лекарств РФ. ГРЛС, ЖНВЛП и Росздравнадзор ещё не подключены: ответ сообщает, что источник подключается, и не выдаёт пустую карточку как «препарат не найден».

Drug reference MCP client. GRLS, VEDL and recall sources are not connected yet.

> **Это не медицинская консультация.** Сервис не даёт показаний, дозировок,
> оценок совместимости и подбора замен.

## Что умеет сейчас

- Принимает запрос на регистрацию, карточку, поиск, ЖНВЛП, отзыв партии и инструкцию.
- Отвечает честно: `ready: false` и причина — источник ещё не подключён.
- Не подменяет отказ пустым списком препаратов.

## Что не подключено

- ГРЛС (регистрация, карточка, поиск, инструкция)
- Перечень ЖНВЛП и предельные цены
- Письма Росздравнадзора об изъятии партий

## Быстрый старт

```bash
pipx install atomno-mcp-pharma
# или: uvx atomno-mcp-pharma
```

Cursor / Claude Desktop (`mcp.json` / `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pharma": {
      "command": "uvx",
      "args": ["atomno-mcp-pharma"],
      "env": { "MCP_PHARMA_API_KEY": "<ваш-ключ-Pro>" }
    }
  }
}
```

## Переменные окружения

| Переменная | Описание | Обязательна |
|---|---|---|
| `MCP_PHARMA_API_KEY` | Ключ Pro (заголовок X-API-Key). [Получить](https://atomno-mcp.ru/pricing#pharma-pro) | да |
| `MCP_PHARMA_API_BASE` | URL hosted-бэкенда (по умолчанию — прод) | нет |
| `MCP_PHARMA_TIMEOUT` | Таймаут HTTP, сек (default 30) | нет |
| `MCP_PHARMA_LOG_LEVEL` | Уровень логирования (DEBUG/INFO/WARNING/ERROR, default WARNING) | нет |

## Тулы

| Тул | Вход | Что отвечает сейчас |
|---|---|---|
| `check_drug_registration` | name? / mnn? / ru_number? | `ready: false` — ГРЛС не подключён |
| `get_drug_card` | name? / ru_number? | `ready: false` — ГРЛС не подключён |
| `search_drug` | query, limit? | `ready: false` — ГРЛС не подключён |
| `get_zhnvlp_price` | name? / mnn? | `ready: false` — ЖНВЛП не подключён |
| `check_recall` | name? / series? | `ready: false` — Росздравнадзор не подключён |
| `get_instruction` | name? / ru_number? | `ready: false` — ГРЛС не подключён |

Каждый ответ содержит `source`, `checked_at` и `disclaimer`.

## Дисклеймер

Госреестры ещё не подключены. Это **не** медицинская консультация, назначение
или рекомендация. Не аффилировано с Минздравом РФ и Росздравнадзором.

## Лицензия

MIT © Atomno

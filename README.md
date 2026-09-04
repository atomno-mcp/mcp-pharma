<!-- mcp-name: io.github.atomno-mcp/mcp-pharma -->

# atomno-mcp-pharma

Клиент справочника лекарств РФ. Ответ — из официальной суточной выгрузки ГРЛС и реестра предельных цен ЖНВЛП (Минздрав). Это справка из государственного реестра, а не медицинский совет.

Drug reference MCP client. Official Minzdrav GRLS dump and VEDL ceiling prices.

> **Это справка из государственного реестра, а не медицинский совет.**

## Что умеет сейчас

- Поиск препарата по торговому названию или МНН.
- Карточка регистрационного удостоверения: статус, держатель, даты, формы, производитель.
- Предельная цена по перечню ЖНВЛП, если позиция есть в реестре цен.

## Что архивом не закрывается

- Письма Росздравнадзора об отзыве серий — в выгрузке ГРЛС их нет. Ответ: `ready: false` и причина.
- Текст инструкции — в архиве только реквизиты регистрации, не файл инструкции. Ответ: `ready: false` и причина.

Пустой список препаратов не подменяет отказ источника.

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

| Тул | Вход | Что отвечает |
|---|---|---|
| `check_drug_registration` | name? / mnn? / ru_number? | статус РУ, держатель, даты |
| `get_drug_card` | name? / ru_number? | карточка из ГРЛС |
| `search_drug` | query, limit? | список совпадений |
| `get_zhnvlp_price` | name? / mnn? | предельные цены ЖНВЛП |
| `check_recall` | name? / series? | `ready: false` — писем Росздравнадзора в выгрузке нет |
| `get_instruction` | name? / ru_number? | `ready: false` — текста инструкции в выгрузке нет |

Каждый ответ содержит `source`, `checked_at` и `disclaimer`.

## Дисклеймер

Это справка из государственного реестра, а не медицинский совет. Не аффилировано с Минздравом РФ и Росздравнадзором.

## Лицензия

MIT © Atomno

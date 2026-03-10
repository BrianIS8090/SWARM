# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Обзор проекта

SWARM — локальная CLI-система оркестрации для координации нескольких LLM-агентов (Claude, Codex, Gemini, OpenCode, Qwen), работающих параллельно над общей кодовой базой. Агенты получают задачи из общей SQLite-БД, блокируют файлы для предотвращения конфликтов и завершают задачи с резюме.

## Команды разработки

```bash
# Установка в dev-режиме
pip install -e ".[dev]"

# Запуск всех тестов
pytest

# Запуск одного теста
pytest tests/test_db.py::TestAgents::test_register_agent

# Запуск по файлу
pytest tests/test_cli.py

# Линтинг
ruff check src/ tests/

# Автоисправление
ruff check --fix src/ tests/
```

## Архитектура

### Точка входа
`src/swarm/cli.py` — главное Typer-приложение, регистрирует все подкоманды. Entry point: `swarm = "swarm.cli:app"`.

### Слой данных
- `src/swarm/models.py` — dataclass-модели (`Agent`, `Task`, `FileLock`, `TaskLogEntry`) с enum-ами статусов. Каждая модель имеет `from_row(tuple)` для десериализации из SQLite.
- `src/swarm/db.py` — все операции с SQLite: CRUD для агентов/задач/блокировок/логов. Используется WAL-режим для конкурентного доступа. Транзакции `BEGIN IMMEDIATE` для атомарного захвата задач (`claim_next_task`) и их завершения (`complete_task`).

### Команды (`src/swarm/commands/`)
Каждый файл — одна группа команд:
- `agent.py` — join, agents, next, done, status
- `task.py` — task add/list/close/assign (Typer sub-app)
- `lock.py` — lock, unlock (с ожиданием и таймаутом)
- `monitor.py` — live-дашборд на Rich (4 панели)
- `tui.py` — полноценный TUI на Textual с DataTable
- `start.py` — информационная команда старта
- `logs.py` — журнал событий

### Идентификация агентов
Агенты идентифицируются по имени (`--agent <имя>`) или через файл сессии `.swarm/sessions/.swarm_session_<имя>` + переменные окружения `SWARM_AGENT`/`SWARM_SESSION`. Это позволяет запускать несколько агентов одного типа CLI.

### Система блокировок
Файлы сортируются перед блокировкой (предотвращение дедлоков). При занятости — цикл ожидания с heartbeat-обновлениями. Блокировки снимаются автоматически при `swarm done`.

## Тестирование

- **Фреймворк:** pytest с typer.testing.CliRunner для CLI-тестов
- **Фикстуры** (`tests/conftest.py`): `temp_db` — временная БД с `chdir`, `sample_agent`, `sample_task`
- Тесты делятся на unit (`test_db.py`, `test_agents.py`) и интеграционные CLI (`test_cli.py`)

## Стек

- Python 3.11+, hatchling (build), typer (CLI), rich (вывод), textual (TUI)
- SQLite с WAL-режимом
- ruff для линтинга (line-length=120, B008 игнорируется для Typer-паттернов)

## Конвенции

- Весь UI и комментарии на русском языке
- Отступ: 2 пробела
- Все CLI-команды агента принимают `--agent <имя>` для явной идентификации

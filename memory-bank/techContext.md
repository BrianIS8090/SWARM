# SWARM — Технологический контекст

## Технологический стек

### Основные технологии
| Технология | Назначение | Обоснование |
|---|---|---|
| Python 3.11+ | CLI-приложение, бизнес-логика | Богатая экосистема, typer/rich |
| SQLite (WAL) | Центральная БД | Без конфигурации, атомарные транзакции |
| Typer | CLI-фреймворк | Type-hints, автогенерация help |
| Rich | Терминальный UI / дашборд | Таблицы, live-обновление, панели |
| Click (через Typer) | Парсинг аргументов | Поставляется с Typer |

### Инструменты разработки
| Инструмент | Назначение |
|---|---|
| pytest | Юнит- и интеграционное тестирование |
| ruff | Линтинг и форматирование |
| pre-commit | Git-хуки для контроля качества |

## Структура проекта (планируемая)
```
swarm/
├── pyproject.toml          # Зависимости и метаданные
├── src/
│   └── swarm/
│       ├── __init__.py
│       ├── cli.py          # Точка входа Typer CLI
│       ├── db.py           # Работа с SQLite
│       ├── models.py       # Dataclass-модели
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── init.py     # swarm init
│       │   ├── task.py     # swarm task add/list
│       │   ├── agent.py    # swarm join/agents/status
│       │   ├── lock.py     # swarm lock/unlock
│       │   └── monitor.py  # swarm monitor
│       └── utils.py        # Вспомогательные функции
├── tests/
│   ├── test_db.py
│   ├── test_tasks.py
│   └── test_agents.py
└── SKILLS.md               # Инструкция для агентов
```

## Зависимости (планируемые)
```toml
[project.dependencies]
typer = ">=0.9.0"
rich = ">=13.0.0"
```

## База данных
- SQLite с WAL-режимом для параллельного чтения
- Файл `swarm.db` создаётся в рабочей директории
- Session token хранится в `.swarm_session`

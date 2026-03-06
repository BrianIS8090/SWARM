# M-5: Рефакторинг db.py на подмодули

**Статус:** Отложено
**Приоритет:** MAJOR
**Источник:** FIX_PLAN.md

## Проблема

`src/swarm/db.py` — God Module (~680 строк). Все CRUD-операции, бизнес-логика, управление сессиями и проверка PID в одном файле.

## План

Разделить на подмодули:

```
src/swarm/db/
  __init__.py          — реэкспорт публичного API (обратная совместимость)
  connection.py        — get_connection, init_database, find_db_path, get_db_path, SCHEMA_SQL
  agents.py            — register_agent, get_agent_by_session/name, get_all_agents, update_*, cleanup_dead_agents, is_process_alive
  tasks.py             — create_task, get_task, get_all_tasks, assign_task_to_agent, claim_next_task, complete_task, force_close_task, _has_dependency_cycle
  locks.py             — try_lock_file, get_file_lock, get_all_locks, get_agent_lock, unlock_file, unlock_task_files
  events.py            — log_event, get_recent_events
  sessions.py          — save_session_token, load_session_token, get_current_agent, _detect_shell_command
```

## Ограничения

- `__init__.py` должен реэкспортировать все публичные функции, чтобы существующие импорты `from swarm.db import ...` продолжали работать.
- Константы `DB_FILENAME`, `SESSION_ENV_VAR`, `SESSION_FILENAME`, `AGENT_NAME_RE` вынести в `connection.py` или отдельный `constants.py`.
- После рефакторинга все 96 тестов должны проходить без изменений.

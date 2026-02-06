"""
Команда swarm init.

Инициализирует среду SWARM в текущей директории:
- Создаёт файл swarm.db с полной схемой
- Включает WAL-режим
- Создаёт папки с SKILL.md для каждого типа агента
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from ..db import DB_FILENAME, init_database

console = Console()


# Типы CLI-агентов и их папки
CLI_TYPES = ["claude", "codex", "gemini", "opencode", "qwen"]


def get_skill_template(cli_type: str) -> str:
    """Генерирует SKILL.md для конкретного типа агента."""
    return f'''---
name: swarm-agent
description: Инструкция для {cli_type.capitalize()}-агента по работе в системе SWARM. Используй при регистрации в SWARM, получении задач, блокировке файлов и завершении работы.
---

# SWARM — Инструкция для {cli_type.capitalize()}-агента

## Обзор

Ты — {cli_type.capitalize()}-агент в системе SWARM. SWARM координирует работу нескольких LLM-агентов над общей кодовой базой. Лидер (человек) создаёт задачи, а ты выполняешь их по очереди.

## Регистрация

### ⛔ ОБЯЗАТЕЛЬНО СПРОСИ У ПОЛЬЗОВАТЕЛЯ:

**Перед регистрацией ты ОБЯЗАН спросить у пользователя:**
1. **Какое имя использовать?** (например: "{cli_type}1", "bot-alex", "worker3")
2. **Какая роль?** (architect / developer / tester / devops)

**НЕ ПРИДУМЫВАЙ ИМЯ И РОЛЬ САМОСТОЯТЕЛЬНО!** Жди ответа пользователя.

### После получения ответа:

```bash
swarm join --cli {cli_type} --name <имя-от-пользователя> --role <роль-от-пользователя>
```

**Роли:** `architect`, `developer`, `tester`, `devops`

### После регистрации: ЗАПОМНИ СВОЁ ИМЯ!

Ты будешь использовать его во ВСЕХ последующих командах через `--agent`.

## Цикл работы

После команды Лидера "начинай работать" выполняй цикл:

```
1. swarm next --agent <твоё-имя>              → получить задачу
2. Проанализировать                            → определить файлы для изменения
3. swarm lock <файлы> --agent <твоё-имя>      → заблокировать файлы
4. Выполнить работу                            → написать код
5. swarm done --summary "..." --agent <твоё-имя> → завершить с резюме
6. Повторить с шага 1
```

## Команды

**ВАЖНО:** Всегда добавляй `--agent <твоё-имя>` к командам!

| Команда | Описание |
|---------|----------|
| `swarm join --cli {cli_type} --name X --role Y` | Зарегистрироваться |
| `swarm next --agent X` | Получить задачу |
| `swarm lock файлы --agent X` | Заблокировать файлы |
| `swarm done --summary "..." --agent X` | Завершить задачу |
| `swarm status --agent X` | Проверить свой статус |

## Правила блокировки

- **ВСЕГДА** блокируй файлы перед редактированием
- Указывай **ВСЕ** файлы одной командой
- Если файл занят — команда ждёт автоматически
- Блокировки снимаются при `swarm done`

## Формат резюме

```bash
swarm done --summary "Добавлен UserController с CRUD, файлы: user.py, models.py" --agent <твоё-имя>
```

Кратко: что сделано + какие файлы изменены.

## Важно

- Нет задач → остановись и жди
- Не спрашивай "что дальше?" — просто жди
- Не редактируй файлы без блокировки
- Не модифицируй swarm.db напрямую
'''


def init_command(
    force: bool = typer.Option(False, "--force", "-f", help="Перезаписать существующую БД"),
):
    """
    Инициализирует среду SWARM.
    
    Создаёт swarm.db и папки со SKILL.md для каждого типа агента.
    """
    current_dir = Path.cwd()
    db_path = current_dir / DB_FILENAME

    # Проверяем существование БД
    if db_path.exists() and not force:
        console.print(
            f"[yellow]⚠ Файл {DB_FILENAME} уже существует.[/yellow]\n"
            "Используйте --force для перезаписи.",
        )
        raise typer.Exit(1)

    # Удаляем старую БД если force
    if db_path.exists() and force:
        db_path.unlink()
        # Удаляем также WAL-файлы
        wal_path = current_dir / f"{DB_FILENAME}-wal"
        shm_path = current_dir / f"{DB_FILENAME}-shm"
        if wal_path.exists():
            wal_path.unlink()
        if shm_path.exists():
            shm_path.unlink()

    # Создаём БД
    try:
        init_database(current_dir)
    except Exception as e:
        console.print(f"[red]✗ Ошибка создания базы данных: {e}[/red]")
        raise typer.Exit(1)

    # Создаём структуру папок для каждого типа агента
    skills_created = []
    for cli_type in CLI_TYPES:
        skill_dir = current_dir / f".{cli_type}" / "skills" / "swarm-agent"
        skill_file = skill_dir / "SKILL.md"
        
        if not skill_file.exists() or force:
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(get_skill_template(cli_type), encoding="utf-8")
            skills_created.append(cli_type)

    # Выводим результат
    console.print()
    
    skills_info = ""
    if skills_created:
        skills_info = "\n\nСозданы SKILL.md для агентов:\n"
        for cli_type in skills_created:
            skills_info += f"  • [cyan].{cli_type}/skills/swarm-agent/SKILL.md[/cyan]\n"
    
    console.print(Panel.fit(
        "[green]✓ SWARM инициализирован успешно![/green]\n\n"
        f"База данных: [cyan]{db_path}[/cyan]"
        + skills_info,
        title="SWARM Init",
        border_style="green",
    ))
    console.print()
    console.print("Следующие шаги:")
    console.print("  1. Создайте задачи: [cyan]swarm task add --desc \"...\" --priority 1[/cyan]")
    console.print("  2. Запустите терминалы агентов и выполните [cyan]swarm join[/cyan]")
    console.print("  3. Откройте монитор: [cyan]swarm tui[/cyan]")
    console.print()

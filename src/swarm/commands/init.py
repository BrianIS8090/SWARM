"""
Команда swarm init.

Инициализирует среду SWARM в текущей директории:
- Создаёт файл swarm.db с полной схемой
- Включает WAL-режим
- Генерирует файл SKILLS.md
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from ..db import DB_FILENAME, init_database

console = Console()


# Шаблон SKILLS.md для агентов
SKILLS_TEMPLATE = '''# SWARM — Инструкция для агента

## Обзор системы

SWARM — это система оркестрации, которая координирует работу нескольких LLM-агентов над общей кодовой базой. Ты — один из агентов. Лидер (человек-оператор) создаёт задачи, а ты выполняешь их по очереди.

## Регистрация

Для начала работы зарегистрируйся в системе:

```bash
swarm join
```

Система запросит:
- **Тип CLI**: введи `claude`, `codex` или `gemini` — в зависимости от того, какой инструмент ты представляешь
- **Имя агента**: выбери уникальное имя (например, `alice`, `bob`, `architect-1`)
- **Роль**: выбери одну из ролей: `architect`, `developer`, `tester`, `devops`

## Цикл выполнения задач

После регистрации и команды Лидера "начинай работать" выполняй следующий цикл:

1. **Получи задачу:**
   ```bash
   swarm next
   ```

2. **Проанализируй задачу.** Определи, какие файлы нужно изменить.

3. **Заблокируй файлы ПЕРЕД редактированием:**
   ```bash
   swarm lock файл1.py файл2.py
   ```
   Если файл занят — команда будет ждать его освобождения.

4. **Выполни работу.** Напиши код, внеси изменения.

5. **Заверши задачу с резюме:**
   ```bash
   swarm done --summary "Добавлен REST API для пользователей, создан UserController"
   ```
   Это автоматически снимет все блокировки.

6. **Немедленно запроси следующую задачу:**
   ```bash
   swarm next
   ```

7. **Если задач нет** — остановись и жди следующей команды Лидера. НЕ спрашивай "что делать дальше?" — просто жди.

## Правила блокировки файлов

- **ВСЕГДА** блокируй файлы перед редактированием
- Блокируй **ВСЕ** файлы, которые планируешь изменить, одной командой
- Если файл занят — жди, не пытайся обойти блокировку
- Блокировки снимаются автоматически при `swarm done`

## Рекомендации по резюме

Хорошее резюме:
- Кратко описывает что было сделано
- Перечисляет ключевые изменения
- Упоминает созданные/изменённые файлы

Примеры:
- "Добавлен класс UserRepository с CRUD-операциями, файлы: user_repo.py, models.py"
- "Исправлена ошибка валидации email, добавлены юнит-тесты"
- "Рефакторинг: вынесены общие функции в utils.py"

## Обработка ошибок

- **Нет задач** → Остановись и жди команды Лидера
- **Таймаут блокировки** → Сообщи о проблеме и пропусти задачу
- **Ошибка выполнения** → Заверши задачу с описанием проблемы

## Запрещённые действия

❌ НИКОГДА не редактируй файлы без предварительной блокировки
❌ НИКОГДА не вызывай `swarm done` без выполнения задачи
❌ НИКОГДА не модифицируй файл `swarm.db` напрямую
❌ НИКОГДА не пытайся общаться с другими агентами
❌ НИКОГДА не спрашивай Лидера "что делать дальше?" — просто жди

## Проверка статуса

Посмотреть свой текущий статус:
```bash
swarm status
```

## Команды

| Команда | Описание |
|---------|----------|
| `swarm join` | Зарегистрироваться в системе |
| `swarm next` | Получить следующую задачу |
| `swarm lock <файлы>` | Заблокировать файлы |
| `swarm done --summary "..."` | Завершить задачу |
| `swarm status` | Показать свой статус |
'''


def init_command(
    force: bool = typer.Option(False, "--force", "-f", help="Перезаписать существующую БД"),
):
    """
    Инициализирует среду SWARM.
    
    Создаёт swarm.db и SKILLS.md в текущей директории.
    """
    current_dir = Path.cwd()
    db_path = current_dir / DB_FILENAME
    skills_path = current_dir / "SKILLS.md"

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

    # Создаём SKILLS.md
    if not skills_path.exists() or force:
        skills_path.write_text(SKILLS_TEMPLATE, encoding="utf-8")
        skills_created = True
    else:
        skills_created = False

    # Выводим результат
    console.print()
    console.print(Panel.fit(
        "[green]✓ SWARM инициализирован успешно![/green]\n\n"
        f"База данных: [cyan]{db_path}[/cyan]\n"
        f"SKILLS.md: [cyan]{skills_path}[/cyan]"
        + ("" if skills_created else " (уже существует)"),
        title="SWARM Init",
        border_style="green",
    ))
    console.print()
    console.print("Следующие шаги:")
    console.print("  1. Создайте задачи: [cyan]swarm task add --desc \"...\" --priority 1[/cyan]")
    console.print("  2. Запустите терминалы агентов и выполните [cyan]swarm join[/cyan]")
    console.print("  3. Откройте монитор: [cyan]swarm monitor[/cyan]")
    console.print()

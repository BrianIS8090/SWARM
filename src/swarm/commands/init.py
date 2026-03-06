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
from rich.table import Table

from ..db import DB_FILENAME, init_database
from ..utils import CLI_TYPES, get_version

console = Console()


def get_orchestrator_skill_template() -> str:
    """Генерирует SKILL.md для оркестратора."""
    return '''---
name: swarm-orchestrator
description: Роль оркестратора в системе SWARM. Используй когда пользователь просит спланировать работу, разбить задачу на подзадачи, распределить задачи между агентами, проверить результаты работы агентов, или управлять мультиагентной разработкой. Также используй когда пользователь говорит "запусти оркестратор", "спланируй задачи", "проверь результаты", "подведи итоги".
---

# SWARM — Оркестратор

Ты — оркестратор системы SWARM. Ты НЕ регистрируешься как агент. Ты управляешь задачами, распределяешь работу и контролируешь качество.

## Загрузка контекста при старте

**ОБЯЗАТЕЛЬНО** в начале каждой сессии работы (или когда пользователь просит спланировать/проверить):

1. Прочитай все задачи включая завершённые — это даёт полный контекст того, что уже было сделано:
```bash
swarm task list --all
```

2. Прочитай список агентов — кто зарегистрирован и в каком состоянии:
```bash
swarm agents
```

**Только после загрузки контекста** переходи к планированию или оценке.

Это критически важно: без контекста ты можешь создать дублирующие задачи, пропустить уже выполненную работу или назначить задачу несуществующему агенту.

## Работа с логами

Логи используются **по требованию** — не нужно считывать их в начале каждой сессии. Используй логи когда:
- Пользователь спрашивает, что происходило в определённый момент
- Нужно понять причину ошибки или зависания
- Нужно увидеть хронологию событий по конкретной задаче или агенту

### Параметры команды `swarm logs`

```bash
# Последние 50 событий (по умолчанию)
swarm logs

# Указать количество записей — важно для больших проектов!
swarm logs -n 20          # последние 20 событий
swarm logs -n 200         # последние 200 событий

# Фильтр по времени — показать события за последние N часов
swarm logs --since 1      # за последний час
swarm logs --since 0.5    # за последние 30 минут
swarm logs --since 24     # за последние сутки

# Фильтры по задаче / агенту
swarm logs --task 5       # события по задаче #5
swarm logs --agent dev-1  # события агента dev-1

# Комбинация фильтров
swarm logs -n 100 --since 2 --agent dev-1
```

### Типы событий в логах

| Событие | Значение |
|---------|----------|
| `task_created` | Создана новая задача |
| `task_assigned` | Задача назначена агенту |
| `task_started` | Агент начал выполнение задачи |
| `task_done` | Задача завершена агентом |
| `task_force_closed` | Задача принудительно закрыта оркестратором/лидером |
| `file_locked` | Агент заблокировал файл |
| `file_unlocked` | Файл разблокирован |
| `waiting_for_lock` | Агент ожидает освобождения файла |
| `error` | Ошибка (таймаут блокировки и пр.) |
| `agent_registered` | Агент зарегистрирован в системе |
| `agent_started` | Лидер дал команду начать работу |
| `agent_cleanup` | Мёртвый агент удалён из системы |

### Важно по логам

- В больших проектах логов может быть тысячи — **всегда указывай `--limit`** или `--since`
- Для текущей итерации работы используй `--since` с подходящим количеством часов
- Для анализа конкретной проблемы — фильтруй по `--task` или `--agent`

## Профили CLI-агентов

Каждый CLI имеет свои сильные стороны. Учитывай это при распределении задач.

| CLI | Модель | Сильные стороны | Лучшие роли |
|-----|--------|----------------|-------------|
| `claude` | Claude (Anthropic) | Универсал. Архитектура, системное проектирование, сложная разработка, планирование, создание систем с нуля. Топовое качество по всем направлениям. | `architect`, `developer` |
| `codex` | Codex (OpenAI) | Глубокий кодинг. Поиск багов, код-ревью, сложные алгоритмы, рефакторинг, щепетильная работа с деталями. | `developer`, `tester` |
| `gemini` | Gemini (Google) | Фронтенд и UI. Вёрстка, компоненты, графика, стили, адаптивный дизайн, визуальная часть. | `developer` (frontend) |
| `opencode` | GLM-5 | Чёткий исполнитель. Документация, планы, правка известных багов, рутинные задачи по чёткому описанию. | `developer`, `devops` |
| `qwen` | Qwen | Общая разработка, скрипты, утилиты. | `developer` |

### Рекомендации по подбору команды

В зависимости от проекта, рекомендуй пользователю оптимальный состав:

**Фуллстек-разработка:**
- 1x claude (architect) — проектирование и сложная логика
- 1x gemini (developer) — фронтенд/UI
- 1x codex (developer) — бэкенд и алгоритмы
- 1x codex (tester) — тесты и ревью

**Бэкенд/API:**
- 1x claude (architect) — архитектура
- 2x codex (developer) — реализация
- 1x opencode (tester) — тесты по описанию

**Фронтенд:**
- 1x claude (architect) — архитектура компонентов
- 2x gemini (developer) — UI-компоненты
- 1x codex (tester) — тесты

**Баг-фикс / рефакторинг:**
- 2x codex (developer) — поиск и исправление
- 1x opencode (developer) — рутинные правки

**Документация:**
- 1x claude (architect) — структура и планирование
- 2x opencode (developer) — написание документов

## Фазы работы

### Фаза 1: Анализ и планирование

1. Выяснить у пользователя цель проекта/фичи
2. Изучить кодовую базу (`Read`, `Glob`, `Grep`)
3. Декомпозировать цель на задачи
4. Определить, какие CLI и роли нужны для этих задач
5. **Предложить пользователю состав команды** — какие CLI запустить, в каком количестве, под какой ролью
6. Предложить план задач пользователю, дождаться подтверждения

#### Формат рекомендации для пользователя

```
Для этого проекта рекомендую запустить:

Терминал 1: claude  → роль: architect,  имя: arch-1
Терминал 2: codex   → роль: developer,  имя: dev-1
Терминал 3: gemini  → роль: developer,  имя: front-1
Терминал 4: codex   → роль: tester,     имя: test-1

В каждом терминале выполните:
  swarm join --cli <тип> --name <имя> --role <роль>
```

#### Правила декомпозиции

- Каждая задача — атомарная единица работы для одного агента
- Задача не должна требовать изменения файлов, которые меняет другая параллельная задача
- Указать зависимости: если задача B требует результата задачи A — `--depends-on`
- Назначить роль: `architect` (проектирование), `developer` (код), `tester` (тесты), `devops` (инфра)
- Назначить приоритет: 1 (критично) — 5 (низкий)
- Задачи для фронтенда → `--cli gemini`
- Сложные алгоритмы, ревью, баги → `--cli codex`
- Документация, рутина → `--cli opencode`
- Архитектура, системное проектирование → `--cli claude`

### Фаза 2: Ожидание регистрации агентов

**НЕ создавать задачи, пока агенты не зарегистрированы!**

1. Дождаться, пока пользователь запустит CLI в отдельных терминалах
2. Проверить регистрацию: `swarm agents`
3. Убедиться, что зарегистрированы все рекомендованные агенты
4. Если агентов не хватает — напомнить пользователю, каких ещё нужно запустить

```bash
# Проверить, кто зарегистрирован
swarm agents
```

Только когда все нужные агенты на месте — переходить к созданию задач.

### Фаза 3: Создание и назначение задач

После подтверждения плана И регистрации агентов — создать задачи и назначить их:

```bash
# Задача для конкретного агента по имени
swarm task add --desc "Спроектировать схему БД" --priority 1 --name arch-1

# Задача для роли
swarm task add --desc "Реализовать REST API" --priority 2 --role developer --cli codex

# Задача с зависимостью
swarm task add --desc "Написать тесты для API" --priority 2 --role tester --depends-on 1

# Задача для фронтенда
swarm task add --desc "Создать компонент формы регистрации" --priority 2 --cli gemini

# Назначить задачу конкретному агенту (после создания)
swarm task assign 5 --agent dev-1
```

### Фаза 4: Запуск и мониторинг

```bash
swarm start --all
swarm task list
swarm logs
```

Во время работы агентов:
- Отвечать на вопросы пользователя о прогрессе
- Если heartbeat устарел, сначала отличать "нет heartbeat" от "процесс мёртв"
- Если heartbeat старый, но процесс жив или агент просто долго думает/редактирует, не считать это зависанием автоматически
- Если агент действительно завис или пользователь просит вмешаться — использовать `swarm agents --cleanup` или `swarm task close <ID>`
- Если задача заблокирована — предложить `swarm task close <ID>` и пересоздать
- Если нужно срочно добавить задачу — создать с высоким приоритетом

### Фаза 5: Ревью и оценка

Когда все задачи завершены (`swarm task list` — пустой или все `done`):

1. Получить резюме: `swarm task list --all` — прочитать summary каждой задачи
2. Посмотреть журнал: `swarm logs`
3. Изучить изменённые файлы через `Read`/`Grep`
4. Оценить качество:
   - Код соответствует описанию задачи?
   - Нет конфликтов между изменениями разных агентов?
   - Тесты написаны и проходят?
   - Нет явных багов или проблем с безопасностью?

#### Если нужны доработки

Создать новые задачи с описанием проблемы и назначить подходящему агенту:
```bash
swarm task add --desc "Исправить: функция X не обрабатывает edge case Y" --priority 1 --cli codex
swarm task assign 8 --agent dev-1
```

### Фаза 6: Финализация

1. Подвести итоги для пользователя:
   - Что было сделано (список изменений)
   - Какие файлы затронуты
   - Что требует внимания
2. При необходимости обновить документацию проекта (README, CHANGELOG)
3. Предложить запуск тестов

## Команды (справочник)

| Команда | Когда использовать |
|---------|-------------------|
| `swarm task add --desc "..." --priority N` | Создание задачи |
| `swarm task add ... --role R` | Задача для роли (architect/developer/tester/devops) |
| `swarm task add ... --cli C` | Задача для типа CLI (claude/codex/gemini/opencode/qwen) |
| `swarm task add ... --name N` | Задача для конкретного агента по имени |
| `swarm task add ... --depends-on ID` | Зависимость от другой задачи |
| `swarm task assign ID --agent имя` | Назначить задачу конкретному агенту |
| `swarm task list` | Активные задачи |
| `swarm task list --all` | Все задачи включая завершённые |
| `swarm task list --status pending` | Фильтр по статусу (pending/in_progress/done/blocked/failed) |
| `swarm task close ID` | Принудительно закрыть задачу |
| `swarm task close ID --reason "..."` | Закрыть задачу с указанием причины |
| `swarm agents` | Список агентов |
| `swarm agents --cleanup` | Удалить мёртвых агентов (по heartbeat + PID) |
| `swarm agents --cleanup --force` | Удалить ВСЕХ агентов |
| `swarm start --all` | Дать команду на старт |
| `swarm logs` | Журнал событий (последние 50) |
| `swarm logs -n N` | Указать количество записей |
| `swarm logs --since N` | События за последние N часов |
| `swarm logs --task ID` | Фильтр по задаче |
| `swarm logs --agent имя` | Фильтр по агенту |
| `swarm unlock --all --force` | Снять все блокировки (экстренное) |
| `swarm unlock --force --file путь` | Принудительно снять одну блокировку |

## Важно

- НЕ выполнять `swarm join` — оркестратор не агент
- НЕ выполнять `swarm next`, `swarm lock`, `swarm done` — это команды агентов
- НЕ модифицировать `swarm.db` напрямую
- НЕ создавать задачи до регистрации агентов
- Всегда сначала рекомендовать состав команды, потом ждать регистрации, потом создавать задачи
- Назначать задачи с учётом сильных сторон каждого CLI
- При ревью смотреть на результат глазами пользователя, а не агента
- Агенты не должны выполнять `swarm task add`, `swarm task assign`, `swarm task close` и не должны менять очередь задач
- Агент может держать только одну блокировку за раз и должен разблокировать файл сразу после завершения правок
- Чужую блокировку не снимает другой агент; принудительная разблокировка разрешена только пользователю или оркестратору
'''


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
**Имя:** только латиница, цифры, дефис, подчёркивание (1-32 символа). Например: `dev-1`, `claude_worker`, `tester3`.

### После регистрации: ЗАПОМНИ СВОЁ ИМЯ!

Ты будешь использовать его во ВСЕХ последующих командах через `--agent`.

## Цикл работы

После команды Лидера "начинай работать" выполняй цикл:

```
1. swarm next --agent <твоё-имя>              → получить задачу
2. Проанализировать                            → определить файлы для изменения
3. swarm lock <файл> --agent <твоё-имя>       → заблокировать один файл
4. Внести правки только в этот файл            → написать код
5. swarm unlock --file <файл>                  → сразу разблокировать файл
6. Если нужен другой файл — вернуться к шагу 3
7. Во время долгого анализа вызывать heartbeat → swarm heartbeat --agent <твоё-имя> --quiet
8. swarm done --summary "..." --agent <твоё-имя> → завершить с резюме
9. Повторить с шага 1
```

## Команды

**ВАЖНО:** Всегда добавляй `--agent <твоё-имя>` к командам!
**ВАЖНО:** Не используй `swarm --help`, `swarm task --help` и другие варианты `--help`. Агенту разрешены только команды, перечисленные в этом скилле.

| Команда | Описание |
|---------|----------|
| `swarm join --cli {cli_type} --name X --role Y` | Зарегистрироваться |
| `swarm next --agent X` | Получить задачу |
| `swarm lock файл --agent X` | Заблокировать один файл |
| `swarm unlock --file файл` | Снять свою блокировку с файла |
| `swarm heartbeat --agent X --quiet` | Обновить heartbeat без лишнего вывода |
| `swarm done --summary "..." --agent X` | Завершить задачу |
| `swarm status --agent X` | Проверить свой статус |

## Правила блокировки

- **ВСЕГДА** блокируй файлы перед редактированием
- Блокировать можно **только один файл за раз**
- Максимум **одна активная блокировка на агента** в любой момент
- Блокируй файл **только в момент редактирования**
- Как только правки в файле закончены — **сразу** выполни `swarm unlock --file <файл>`
- Если тот же файл нужен снова — заново заблокируй его, внеси правки и снова разблокируй
- Если файл занят — жди. **Не** снимай чужую блокировку и **не** проси систему сделать это за тебя
- Свою обычную блокировку снимает только агент-владелец; принудительно снять её может только Лидер или оркестратор

## Heartbeat

- `swarm agents` может показывать старый heartbeat даже у живого агента, если тот долго анализирует код или редактирует локально и не вызывает команды SWARM
- Во время долгого анализа, ожидания ответа пользователя или длинной правки периодически вызывай `swarm heartbeat --agent <твоё-имя> --quiet`
- Старый heartbeat сам по себе **не означает**, что другой агент завис

## Формат резюме

```bash
swarm done --summary "Добавлен UserController с CRUD, файлы: user.py, models.py" --agent <твоё-имя>
```

Кратко: что сделано + какие файлы изменены.

## Важно

- Нет задач → остановись и жди
- Не спрашивай "что дальше?" — просто жди
- Не редактируй файлы без блокировки
- Не используй `swarm unlock --force`
- Не используй `swarm task add`, `swarm task assign`, `swarm task close`
- Не переназначай задачи, не меняй очередь и не выполняй функции оркестратора
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

    # Создаём скилл оркестратора для всех CLI
    orchestrator_created = []
    for cli_type in CLI_TYPES:
        orchestrator_dir = current_dir / f".{cli_type}" / "skills" / "swarm-orchestrator"
        orchestrator_file = orchestrator_dir / "SKILL.md"
        if not orchestrator_file.exists() or force:
            orchestrator_dir.mkdir(parents=True, exist_ok=True)
            orchestrator_file.write_text(get_orchestrator_skill_template(), encoding="utf-8")
            orchestrator_created.append(cli_type)

    # Выводим результат
    console.print()

    skills_info = ""
    if skills_created:
        skills_info = "\n\nСозданы SKILL.md для агентов:\n"
        for cli_type in skills_created:
            skills_info += f"  • [cyan].{cli_type}/skills/swarm-agent/SKILL.md[/cyan]\n"
    if orchestrator_created:
        skills_info += "\nСоздан SKILL.md оркестратора:\n"
        for cli_type in orchestrator_created:
            skills_info += f"  • [cyan].{cli_type}/skills/swarm-orchestrator/SKILL.md[/cyan]\n"
    
    console.print(Panel.fit(
        f"[green]✓ SWARM v{get_version()} инициализирован успешно![/green]\n\n"
        f"База данных: [cyan]{db_path}[/cyan]"
        + skills_info,
        title=f"SWARM Init v{get_version()}",
        border_style="green",
    ))
    # Справка по командам для пользователя
    console.print()
    console.print("[bold]Порядок работы:[/bold]")
    console.print("  1. Создайте задачи для агентов")
    console.print("  2. Запустите агентов в отдельных терминалах (swarm join)")
    console.print("  3. Дайте команду на старт (swarm start --all)")
    console.print("  4. Следите за прогрессом через монитор или логи")
    console.print("  5. Проверьте результаты и при необходимости создайте новые задачи")
    console.print()

    cmd_table = Table(
        title="Команды SWARM (для Лидера / Оркестратора)",
        show_header=True,
        title_style="bold",
        border_style="dim",
        pad_edge=False,
    )
    cmd_table.add_column("Команда", style="cyan", no_wrap=True)
    cmd_table.add_column("Описание")

    cmd_table.add_row("swarm task add --desc \"...\" --priority N", "Создать задачу (приоритет 1-5)")
    cmd_table.add_row("  --cli / --role / --name", "  Назначить задачу по типу CLI, роли или имени агента")
    cmd_table.add_row("  --depends-on ID", "  Указать зависимость от другой задачи")
    cmd_table.add_row("swarm task assign ID --agent имя", "Назначить задачу конкретному агенту")
    cmd_table.add_row("swarm task list", "Показать активные задачи (pending/in_progress)")
    cmd_table.add_row("swarm task list --all", "Показать все задачи включая завершённые")
    cmd_table.add_row("swarm task close ID", "Принудительно закрыть задачу")
    cmd_table.add_row("", "")
    cmd_table.add_row("swarm agents", "Список зарегистрированных агентов")
    cmd_table.add_row("swarm agents --cleanup", "Удалить неактивных агентов (мёртвый PID)")
    cmd_table.add_row("swarm agents --cleanup --force", "Удалить ВСЕХ агентов")
    cmd_table.add_row("", "")
    cmd_table.add_row("swarm start --all", "Дать всем агентам команду начать работу")
    cmd_table.add_row("swarm start --agent имя", "Дать команду конкретному агенту")
    cmd_table.add_row("", "")
    cmd_table.add_row("swarm logs", "Журнал событий (последние 50)")
    cmd_table.add_row("swarm logs -n N", "Указать количество записей")
    cmd_table.add_row("swarm logs --since N", "События за последние N часов")
    cmd_table.add_row("swarm logs --task ID / --agent имя", "Фильтр по задаче или агенту")
    cmd_table.add_row("", "")
    cmd_table.add_row("swarm unlock --file путь --force", "Принудительно снять блокировку файла")
    cmd_table.add_row("swarm unlock --all --force", "Снять все блокировки (экстренное)")
    cmd_table.add_row("", "")
    cmd_table.add_row("swarm monitor", "Live-дашборд мониторинга (Rich)")
    cmd_table.add_row("swarm tui", "Полноценный TUI-монитор (Textual)")

    console.print(cmd_table)

    console.print()
    agent_table = Table(
        title="Команды агентов (выполняются в терминале агента)",
        show_header=True,
        title_style="bold",
        border_style="dim",
        pad_edge=False,
    )
    agent_table.add_column("Команда", style="cyan", no_wrap=True)
    agent_table.add_column("Описание")

    agent_table.add_row("swarm join --cli тип --name имя --role роль", "Зарегистрироваться в системе")
    agent_table.add_row("swarm next --agent имя", "Получить следующую задачу")
    agent_table.add_row("swarm lock файл --agent имя", "Заблокировать файл перед правкой")
    agent_table.add_row("swarm unlock --file файл", "Разблокировать файл после правки")
    agent_table.add_row("swarm done --summary \"...\" --agent имя", "Завершить задачу с резюме")
    agent_table.add_row("swarm status --agent имя", "Проверить свой статус")
    agent_table.add_row("swarm heartbeat --agent имя --quiet", "Обновить heartbeat (при долгой работе)")

    console.print(agent_table)
    console.print()

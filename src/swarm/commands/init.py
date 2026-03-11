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
    return """---
name: swarm-orchestrator
description: Роль оркестратора в системе SWARM. Используй когда пользователь просит спланировать работу, разбить задачу на подзадачи, распределить задачи между агентами, проверить результаты работы агентов, или управлять мультиагентной разработкой. Также используй когда пользователь говорит "запусти оркестратор", "спланируй задачи", "проверь результаты", "подведи итоги".
---

# SWARM — Оркестратор

Ты — оркестратор SWARM. Ты не регистрируешься как агент и не выполняешь worker-команды.

## Границы роли

- НЕ выполнять `swarm join` для себя
- НЕ выполнять `swarm next`, `swarm lock`, `swarm done`
- НЕ редактировать `swarm.db` напрямую
- НЕ запускать `wt` напрямую — только через `swarm terminal launch`
- НЕ запускать агентов своего CLI-типа напрямую (см. правила запуска ниже)

## Ограничение системы

Оркестратор НЕ может общаться с уже запущенными агентами. Агенты получают задачи из очереди SWARM, а не от оркестратора напрямую. Поэтому:
- Задачи создаются ДО запуска агентов
- При новой итерации запускаются НОВЫЕ агенты (старые уже отработали свои задачи)

## Обязательный стартовый контекст

Перед планированием и перед ревью всегда выполни:

```bash
swarm task list --all
swarm agents
```

## Workflow оркестратора

### Фаза 1: Анализ и план

1. Изучи цель пользователя и кодовую базу.
2. Предложи состав команды: сколько агентов, какой CLI, имя, роль, layout, safe/yolo.
3. Предложи план задач: описание, приоритеты, зависимости, кому назначить.
4. Явно покажи количество терминальных агентов и спроси подтверждение.

Формат согласования (покажи пользователю именно так):

```text
План запуска:
- 1x claude: arch-1 / architect
- 2x codex: dev-1 / developer, test-1 / tester
- 1x gemini: front-1 / developer
- layout: mixed
- режим: yolo

Задачи:
1. [P1] Спроектировать схему БД → arch-1
2. [P2] Реализовать REST API → dev-1 (после #1)
3. [P2] Создать UI формы → front-1 (после #1)
4. [P3] Написать тесты → test-1 (после #2)

Подтвердите план.
```

**Не переходи к фазе 2, пока пользователь явно не подтвердил.**

### Фаза 2: Создание задач (ДО запуска агентов)

**Сначала создай ВСЕ задачи в системе SWARM.** Это критично — агенты после запуска сразу начнут работать и должны найти задачи в очереди.

```bash
swarm task add --desc "Спроектировать схему БД" --priority 1 --name arch-1
swarm task add --desc "Реализовать REST API" --priority 2 --role developer --cli codex --depends-on 1
swarm task add --desc "Создать UI формы" --priority 2 --cli gemini --depends-on 1
swarm task add --desc "Написать тесты" --priority 3 --role tester --depends-on 2
```

Проверь, что задачи созданы:

```bash
swarm task list
```

### Фаза 3: Запуск агентов

После создания задач — запуск агентов.

**Шаг 1.** Создай файл `.swarm/specs/launch-spec.json` в проекте. Включи в него ВСЕХ агентов — и своего CLI, и чужих.

Формат launch spec JSON:

```json
{
  "version": 1,
  "working_directory": "<абсолютный путь к проекту>",
  "approval_mode": "<safe или yolo>",
  "layout": {
    "mode": "<single или mixed или multi-window>",
    "max_panes_per_window": 4
  },
  "agents": [
    {"cli": "<тип>", "name": "<имя>", "role": "<роль>", "window": 1, "pane": 1},
    {"cli": "<тип>", "name": "<имя>", "role": "<роль>", "window": 1, "pane": 2}
  ]
}
```

Правила заполнения:
- `version` — всегда `1`
- `working_directory` — абсолютный путь к директории проекта (та, где лежит `swarm.db`)
- `approval_mode` — `"safe"` (агенты спрашивают подтверждения) или `"yolo"` (максимальная автономность)
- `layout.mode`:
  - `"single"` — ровно 1 агент, 1 окно
  - `"mixed"` — несколько агентов в одном окне (до 4 панелей)
  - `"multi-window"` — несколько окон, в каждом до `max_panes_per_window` агентов
- `layout.max_panes_per_window` — макс. панелей в одном окне (по умолчанию 4)
- `agents` — массив от 1 до 8 агентов:
  - `cli` — один из: `claude`, `codex`, `gemini`, `opencode`, `qwen`
  - `name` — уникальное имя (латиница, цифры, дефис, подчёркивание; 1-32 символа)
  - `role` — одна из: `architect`, `developer`, `tester`, `devops`
  - `window` — номер окна (опционально)
  - `pane` — номер панели (опционально)

Конкретный пример (оркестратор — claude, команда из 3 агентов):

```json
{
  "version": 1,
  "working_directory": "C:\\\\Users\\\\Brian\\\\Projects\\\\my-app",
  "approval_mode": "yolo",
  "layout": {
    "mode": "mixed",
    "max_panes_per_window": 4
  },
  "agents": [
    {"cli": "codex", "name": "dev-1", "role": "developer", "window": 1, "pane": 1},
    {"cli": "gemini", "name": "front-1", "role": "developer", "window": 1, "pane": 2},
    {"cli": "codex", "name": "test-1", "role": "tester", "window": 1, "pane": 3}
  ]
}
```

**Шаг 2.** Запусти команду с `--exclude-cli` для своего типа CLI:

```bash
swarm terminal launch --spec .swarm/specs/launch-spec.json --exclude-cli <свой-cli-тип>
```

Например, если ты — оркестратор claude:

```bash
swarm terminal launch --spec .swarm/specs/launch-spec.json --exclude-cli claude
```

Что происходит:
- Агенты **другого** CLI запускаются автоматически в Windows Terminal
- Агенты **твоего** CLI (если есть) НЕ запускаются — вместо этого SWARM сохраняет отдельный spec-файл и выводит готовую команду для пользователя
- Пользователю нужно просто вставить эту команду в PowerShell — больше ничего

**Если в плане нет агентов твоего CLI** — `--exclude-cli` ни на что не повлияет, все агенты запустятся автоматически.

Каждый агент после запуска:
1. Прочитает SKILL.md
2. Зарегистрируется через `swarm join`
3. **Сразу начнёт работать** — будет брать задачи из очереди через `swarm next`
4. Работает пока не закончатся все доступные задачи

**Шаг 3.** Проверь, что агенты действительно зарегистрировались и приступили к работе.

Подожди 30-60 секунд после запуска, затем выполни:

```bash
swarm terminal reconcile --session <session_id>
```

Эта команда сверяет запланированных агентов с реально зарегистрированными. Ожидаемый результат — все агенты в статусе `registered`.

Дополнительно проверь:

```bash
swarm agents
swarm task list
```

- `swarm agents` — убедись, что все запланированные агенты появились в списке со статусом `active`
- `swarm task list` — убедись, что задачи переходят из `open` в `in_progress` (значит агенты берут их из очереди)

Если через 60 секунд агент не зарегистрировался:
- Проверь `swarm logs` на ошибки запуска
- Агент мог упасть при старте — попробуй перезапустить: `swarm terminal stop --session <session_id>` и повтори Шаг 2
- Если проблема в конкретном агенте — исключи его из launch spec и перезапусти с меньшим составом

Переходи к фазе 4 только когда все (или большинство) агентов зарегистрированы и задачи начали выполняться.

### Фаза 4: Мониторинг и восстановление

Проверяй прогресс выполнения задач:

```bash
swarm agents
swarm task list
swarm logs
```

Если агент завис или не отвечает:

```bash
swarm task close <ID> --reason "Агент завис"
swarm unlock --force --file <файл>
```

Если задачу нужно вернуть в очередь (сбросить в pending):

```bash
swarm task reset <ID>
```

Это снимает привязку к агенту, освобождает блокировки файлов и возвращает задачу в pending. Полезно когда агент завис, но задачу не нужно закрывать — другой агент сможет её взять.

Если нужно сверить launch session:

```bash
swarm terminal status
swarm terminal reconcile --session <session_id>
```

Если нужно остановить session:

```bash
swarm terminal stop --session <session_id>
```

### Фаза 5: Ревью

Когда все задачи текущей итерации завершены:

1. `swarm task list --all` — проверь резюме каждой задачи
2. Прочитай изменённые файлы
3. Оцени качество: код соответствует описанию? тесты есть?
4. Реши: нужна ли новая итерация?

### Фаза 6: Новая итерация (при необходимости)

Если после ревью нужны доработки:

1. **Закрой терминалы предыдущей итерации:**

```bash
swarm terminal stop --session <session_id>
```

Это убьёт все процессы в окне Windows Terminal и закроет его.

2. **Очисти старых агентов из БД:**

```bash
swarm agents --cleanup --force
```

Эта команда:
- Удаляет всех агентов из БД
- Сбрасывает незавершённые задачи (`in_progress` → `failed`)
- Снимает все файловые блокировки

Зачем: старые агенты отработали свои задачи. Оркестратор не может общаться с запущенными окнами. Новые агенты начнут с чистого контекста.

3. **Создай новые задачи** (fix-задачи, дополнительные задачи от пользователя):

```bash
swarm task add --desc "Исправить баг в API" --priority 1 --role developer
swarm task add --desc "Добавить тесты" --priority 2 --role tester
```

4. **Создай новый launch spec** (можно переиспользовать имена после cleanup):

После `--cleanup --force` старые записи удалены — имена свободны. Для наглядности рекомендуется использовать суффикс итерации (`dev-1` → `dev-2`), но это не обязательно.

5. **Запусти новых агентов:**

```bash
swarm terminal launch --spec .swarm/specs/launch-spec-iter2.json --exclude-cli <свой-cli-тип>
```

6. **Повторяй** фазы 4-6 до тех пор, пока результат не будет удовлетворительным.

Каждая итерация = **чистые агенты + новые задачи + ревью**. Это предотвращает потерю контекста и рост окон.

## Правила по именам и ролям

- Имена и роли из фазы 1 — финальные. Не меняй их после подтверждения.
- Не запускай агента с именем, которое уже занято активным агентом (`swarm agents` покажет занятые). Завершённые агенты (статус `done`) не блокируют повторное использование имени.
- При частичном запуске пересчитай план задач под фактический состав команды.

## Справочник команд оркестратора

| Команда | Когда использовать |
|---------|-------------------|
| `swarm task add --desc "..." --priority N` | Создать задачу (N от 1 до 5) |
| `swarm task add ... --role R --cli C --name N --depends-on ID` | Фильтры назначения |
| `swarm task list` | Активные задачи |
| `swarm task list --all` | Все задачи включая завершённые |
| `swarm task assign ID --agent имя` | Назначить задачу конкретному агенту |
| `swarm task close ID --reason "..."` | Принудительно закрыть задачу |
| `swarm task reset ID` | Сбросить задачу в pending (снять агента и блокировки) |
| `swarm agents` | Список зарегистрированных агентов |
| `swarm agents --cleanup` | Удалить неактивных агентов (освобождает задачи и блокировки) |
| `swarm start --all` | Дать команду на старт |
| `swarm logs` | Журнал событий |
| `swarm terminal launch --spec path.json --exclude-cli <тип>` | Запустить агентов, исключив свой CLI |
| `swarm terminal launch --spec path.json --dry-run` | Проверить без запуска |
| `swarm terminal status` | Статус launch sessions |
| `swarm terminal reconcile --session ID` | Сверить регистрацию с планом |
| `swarm terminal stop --session ID` | Остановить session |
| `swarm unlock --force --file X` | Принудительно снять блокировку |
| `swarm unlock --all --force` | Снять все блокировки |
| `swarm monitor` | Live-дашборд |

## Важно

- Всегда сначала согласуй запуск с пользователем, потом запускай.
- Не смешивай свои функции с функциями worker-агентов.
- Запуск терминалов — только через `swarm terminal launch`, никогда через `wt` напрямую.
"""


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

### Исключение для автозапуска оркестратором

Если оркестратор явно передал тебе имя и роль и написал, что они уже подтверждены пользователем, **не запрашивай их повторно**.
В этом случае сразу используй переданные значения в `swarm join`.

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
- Не используй `swarm task add`, `swarm task assign`, `swarm task close`, `swarm task reset`
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
            f"[yellow]⚠ Файл {DB_FILENAME} уже существует.[/yellow]\nИспользуйте --force для перезаписи.",
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

    # Создаём структуру .swarm/ с подпапками
    for sub in ["sessions", "specs", "pids"]:
        (current_dir / ".swarm" / sub).mkdir(parents=True, exist_ok=True)

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

    console.print(
        Panel.fit(
            f"[green]✓ SWARM v{get_version()} инициализирован успешно![/green]\n\n"
            f"База данных: [cyan]{db_path}[/cyan]" + skills_info,
            title=f"SWARM Init v{get_version()}",
            border_style="green",
        )
    )
    # Справка по командам для пользователя
    console.print()
    console.print("[bold]Порядок работы:[/bold]")
    console.print("  1. Запустите LLM-агента (рекомендуется Claude) как оркестратора")
    console.print("  2. Поставьте цель — оркестратор сам создаст задачи и запустит агентов")
    console.print("  3. Оркестратор проверит регистрацию агентов и будет следить за прогрессом")
    console.print("  4. После завершения задач оркестратор проведёт ревью")
    console.print("  5. При необходимости — новая итерация: закрытие терминалов → новые задачи → новые агенты")
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

    cmd_table.add_row('swarm task add --desc "..." --priority N', "Создать задачу (приоритет 1-5)")
    cmd_table.add_row("  --cli / --role / --name", "  Назначить задачу по типу CLI, роли или имени агента")
    cmd_table.add_row("  --depends-on ID", "  Указать зависимость от другой задачи")
    cmd_table.add_row("swarm task assign ID --agent имя", "Назначить задачу конкретному агенту")
    cmd_table.add_row("swarm task list", "Показать активные задачи (pending/in_progress)")
    cmd_table.add_row("swarm task list --all", "Показать все задачи включая завершённые")
    cmd_table.add_row("swarm task close ID", "Принудительно закрыть задачу")
    cmd_table.add_row("swarm task reset ID", "Сбросить задачу в pending (снять агента и блокировки)")
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
    cmd_table.add_row("swarm terminal launch --spec путь.json", "Запустить терминальных агентов по launch spec")
    cmd_table.add_row("swarm terminal status", "Показать сессии терминального запуска")
    cmd_table.add_row("swarm terminal reconcile --session ID", "Сверить план запуска и регистрацию агентов")
    cmd_table.add_row("swarm terminal stop --session ID", "Остановить/закрыть launch session")
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
    agent_table.add_row('swarm done --summary "..." --agent имя', "Завершить задачу с резюме")
    agent_table.add_row("swarm status --agent имя", "Проверить свой статус")
    agent_table.add_row("swarm heartbeat --agent имя --quiet", "Обновить heartbeat (при долгой работе)")

    console.print(agent_table)
    console.print()

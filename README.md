<div align="center">

# SWARM

**Локальная система оркестрации мультиагентной разработки**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python\&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build System: Hatch](https://img.shields.io/badge/build-hatchling-292929)](https://hatch.pypa.io)
[![CLI: Typer](https://img.shields.io/badge/cli-typer-009688)](https://typer.tiangolo.com)
[![SQLite WAL](https://img.shields.io/badge/db-SQLite%20WAL-003B57?logo=sqlite\&logoColor=white)](https://sqlite.org)

Координируйте нескольких LLM-агентов — **Claude, Codex, Gemini, OpenCode, Qwen** — работающих параллельно над общей кодовой базой. Один из агентов выступает **оркестратором**: анализирует проект, планирует задачи, распределяет работу и контролирует результат.

***

<img width="2752" height="1536" alt="lumigen-zlay5lank" src="https://github.com/user-attachments/assets/545c7248-c30b-43d6-aa8c-af938a7fbf2b" />


<img width="2529" height="1323" alt="SWARM Monitor — live-дашборд" src="https://github.com/user-attachments/assets/0d05ba34-7886-459f-844b-d2132f9f832c" />

</div>

***

## Зачем SWARM?

Современные LLM-агенты (Claude Code, Codex CLI, Gemini CLI и др.) мощны поодиночке, но при параллельной работе над одним проектом неизбежны конфликты: два агента правят один файл, задачи дублируются, прогресс теряется.

SWARM решает это через трёхуровневую модель управления:

```
Вы (Лидер)  →  Оркестратор (LLM)  →  Агенты (LLM в терминалах)
  ставите          планирует,             получают задачи,
  цель             раздаёт задачи,        блокируют файлы,
                   контролирует           пишут код
```

* **Оркестратор** — LLM-агент (обычно Claude), который анализирует проект, декомпозирует цель на задачи, подбирает состав команды и проверяет результат

* **Терминальная оркестрация** — оркестратор сам запускает агентов в Windows Terminal через `swarm terminal launch`, передаёт каждому утверждённые имя и роль

* **Агенты** — LLM в отдельных терминалах, каждый работает по своему циклу: задача → блокировка → код → разблокировка → готово

* **Файловые блокировки** — только один агент редактирует файл в любой момент

* **Полностью локально** — SQLite WAL, никаких облачных зависимостей

***

## Возможности

| <br />               | Возможность              | Описание                                                                 |
| -------------------- | ------------------------ | ------------------------------------------------------------------------ |
| **Оркестрация**      | LLM-оркестратор          | Анализ проекта, декомпозиция задач, подбор команды, ревью результата     |
| **Автозапуск**       | Terminal orchestration   | Оркестратор сам поднимает агентов в Windows Terminal через launch spec   |
| **Мультиагентность** | 5 типов CLI              | Claude, Codex, Gemini, OpenCode, Qwen — с учётом сильных сторон каждого  |
| **Задачи**           | Приоритеты + зависимости | Задачи выполняются в правильном порядке, с фильтрацией по роли/CLI/имени |
| **Роли**             | 4 роли агентов           | `architect`, `developer`, `tester`, `devops`                             |
| **Блокировки**       | Атомарные file locks     | Предотвращение конфликтов при параллельном редактировании                |
| **Мониторинг**       | Rich + Textual           | Live-дашборд и TUI со скроллингом                                        |

***

## Быстрый старт

### 1. Установка

```bash
pip install -e .
```

### 2. Инициализация проекта

```bash
cd ваш-проект
swarm init
```

Создаст `swarm.db` и инструкции `SKILL.md` для каждого типа агента (`.claude/`, `.codex/`, `.gemini/` и др.).

### 3. Запуск оркестратора

Откройте терминал с LLM-агентом (рекомендуется Claude) и скажите ему:

> "Ты оркестратор SWARM. Прочитай SKILL.md оркестратора и спланируй работу над <ваша цель>."
>
> Можно так же направить агента на скилл оркестратора, без явного указания задач. 
>
> После начала работы оркестратор сам попросит указать задачи на выполнения. 

Оркестратор:

1. Изучит кодовую базу
2. Декомпозирует цель на атомарные задачи
3. Предложит состав команды — какие CLI запустить и с какими ролями

```
Для этого проекта рекомендую запустить:

Терминал 1: claude  → роль: architect,  имя: arch-1
Терминал 2: codex   → роль: developer,  имя: dev-1
Терминал 3: gemini  → роль: developer,  имя: front-1
Терминал 4: codex   → роль: tester,     имя: test-1

В каждом терминале выполните:
  swarm join --cli <тип> --name <имя> --role <роль>
```

### 4. Запуск агентов

**Вариант A — Автозапуск через оркестратора (рекомендуется):**

Оркестратор сам формирует launch spec и запускает терминалы:

```bash
swarm terminal launch --spec launch.json
```

Каждый агент получает стартовый промпт с уже утверждёнными именем и ролью, читает SKILL.md и сам выполняет `swarm join`.

**Вариант B — Ручной запуск:**

Откройте отдельный терминал для каждого агента из рекомендации оркестратора (предложения оркестратора — совет, пользователь может указать свой состав).

```bash
# Терминал 2: Codex как developer
codex
# → swarm join --cli codex --name dev-1 --role developer

# Терминал 3: Gemini как frontend developer
gemini
# → swarm join --cli gemini --name front-1 --role developer
```

Каждый агент регистрируется:

```bash
swarm join --cli codex --name dev-1 --role developer
```

### 5. Оркестратор создаёт задачи

После регистрации всех агентов скажите оркестратору:

> "Агенты зарегистрированы. Создавай задачи."

Оркестратор создаст задачи через CLI:

```bash
swarm task add --desc "Спроектировать схему БД" --priority 1 --name arch-1
swarm task add --desc "Реализовать REST API" --priority 2 --role developer --cli codex --depends-on 1
swarm task add --desc "Создать UI формы" --priority 2 --cli gemini --depends-on 1
swarm task add --desc "Написать тесты для API" --priority 3 --role tester --depends-on 2
```

### 6. Запуск работы

Скажите каждому агенту в его терминале:

> "Начинай работать. Работай пока не выполнишь все поставленные задачи"

Каждый агент выполняет цикл:

```
swarm next --agent dev-1          # Получить задачу
swarm lock файл.py --agent dev-1  # Заблокировать файл
# ... правки в коде ...
swarm unlock --file файл.py       # Разблокировать сразу после правок
swarm done --summary "..." --agent dev-1  # Завершить задачу
swarm next --agent dev-1          # Следующая задача
```

### 7. Мониторинг

В отдельном терминале:

```bash
swarm monitor    # Live-дашборд (Rich)
swarm tui        # TUI со скроллингом (Textual) — рекомендуется
```

Или попросите оркестратора проверить прогресс — он выполнит `swarm task list` и `swarm logs`.

### 8. Ревью результата

Когда все задачи завершены, оркестратор:

1. Прочитает резюме каждой задачи (`swarm task list --all`)
2. Изучит изменённые файлы
3. Оценит качество кода
4. При необходимости создаст новые задачи на доработку

***

## Профили CLI-агентов

Оркестратор учитывает сильные стороны каждого CLI при распределении задач:

| CLI        | Сильные стороны                                           | Лучшие роли              |
| ---------- | --------------------------------------------------------- | ------------------------ |
| `claude`   | Архитектура, системное проектирование, сложная разработка | `architect`, `developer` |
| `codex`    | Глубокий кодинг, поиск багов, код-ревью, алгоритмы        | `developer`, `tester`    |
| `gemini`   | Фронтенд, UI-компоненты, вёрстка, стили                   | `developer` (frontend)   |
| `opencode` | Документация, рутинные задачи, правка по описанию         | `developer`, `devops`    |
| `qwen`     | Общая разработка, скрипты, утилиты                        | `developer`              |

### Примеры составов команды

**Фуллстек-разработка:**

* 1x claude (architect) — проектирование и сложная логика

* 1x gemini (developer) — фронтенд/UI

* 1x codex (developer) — бэкенд и алгоритмы

* 1x codex (tester) — тесты и ревью

**Бэкенд/API:**

* 1x claude (architect) — архитектура

* 2x codex (developer) — реализация

* 1x opencode (tester) — тесты

**Баг-фикс / рефакторинг:**

* 2x codex (developer) — поиск и исправление

* 1x opencode (developer) — рутинные правки

***

## Фазы работы оркестратора

```
Фаза 1           Фаза 2              Фаза 3            Фаза 4           Фаза 5           Фаза 6
Анализ     →     Ожидание       →    Создание     →    Мониторинг  →    Ревью       →    Финализация
                 регистрации         задач              работы           результата
                 агентов

Изучить          Предложить           Создать            Следить          Прочитать        Подвести
кодовую          состав               задачи             за               резюме,          итоги,
базу,            команды,             через              прогрессом,      изучить          предложить
декомпозировать  дождаться            CLI,               помогать         код,             тесты
цель             swarm agents         назначить          при зависании    создать fix-задачи
```

***

## Справочник команд

### Команды оркестратора / оператора

| Команда                                    | Описание                                                     |
| ------------------------------------------ | ------------------------------------------------------------ |
| `swarm init`                               | Инициализировать среду SWARM в текущей директории            |
| `swarm task add --desc "..." --priority N` | Создать задачу (`--role`, `--cli`, `--name`, `--depends-on`) |
| `swarm task list`                          | Список активных задач (`--all` — все, `--status pending`)    |
| `swarm task assign <ID> --agent <имя>`     | Назначить задачу конкретному агенту                          |
| `swarm task close <ID>`                    | Принудительно закрыть задачу (`--reason "..."`)              |
| `swarm agents`                             | Список зарегистрированных агентов                            |
| `swarm agents --cleanup`                   | Удалить неактивных агентов (`--force` — всех)                |
| `swarm start --all`                        | Дать команду на старт                                        |
| `swarm monitor`                            | Live-дашборд Rich (`--full`, `--refresh N`)                  |
| `swarm tui`                                | TUI-монитор Textual со скроллингом                           |
| `swarm logs`                               | Журнал событий (`--limit N`, `--agent X`, `--task N`)        |
| `swarm unlock --force --file X`            | Принудительно снять блокировку                               |
| `swarm unlock --all --force`               | Снять все блокировки                                         |

### Терминальная оркестрация

| Команда                                       | Описание                                                      |
| --------------------------------------------- | ------------------------------------------------------------- |
| `swarm terminal launch --spec <path>`         | Запустить агентов по launch spec (`--yes`, `--dry-run`)       |
| `swarm terminal status`                       | Показать активные launch sessions и статус агентов            |
| `swarm terminal reconcile --session <id>`     | Сверить зарегистрированных агентов с планом запуска           |
| `swarm terminal stop --session <id>`          | Остановить launch session и завершить процессы                |

### Команды агента

Все команды агента используют `--agent <имя>`:

| Команда                                         | Описание                                   |
| ----------------------------------------------- | ------------------------------------------ |
| `swarm join --cli TYPE --name NAME --role ROLE` | Зарегистрировать агента                    |
| `swarm next --agent имя`                        | Получить следующую задачу                  |
| `swarm lock <файл> --agent имя`                 | Заблокировать файл на время редактирования |
| `swarm unlock --file <файл>`                    | Снять свою блокировку                      |
| `swarm heartbeat --agent имя --quiet`           | Обновить heartbeat                         |
| `swarm done --summary "..." --agent имя`        | Завершить текущую задачу с резюме          |
| `swarm status --agent имя`                      | Показать статус агента                     |

***

## Правила работы агентов

* Агент может держать **только одну блокировку** одновременно

* Блокировка ставится **только на время фактического редактирования** — сразу после правок `unlock`

* Чужую блокировку агент **не снимает** — принудительная разблокировка только у оркестратора/Лидера

* Агент **не управляет задачами** — `task add`, `task assign`, `task close` выполняет только оркестратор

* При долгом анализе агент вызывает `swarm heartbeat --agent имя --quiet`

***

## Дашборд монитора

```
┌─────────────────────────────┬───────────────────────────────────────────────┐
│       ПАНЕЛЬ АГЕНТОВ        │              ПАНЕЛЬ ЗАДАЧ                     │
│                             │                                               │
│  #1 claude/alice/architect  │  ID  P  Статус    Роль  После Назнач. Работает│
│     Статус: WORKING [#7]    │  #7  1  in_prog   dev    -    alice   alice   │
│     Heartbeat: 12с          │  #8  2  pending   test   #7   bob      -      │
│                             │                                               │
│  #2 codex/bob/developer     │                                               │
│     Статус: IDLE            │                                               │
├─────────────────────────────┼───────────────────────────────────────────────┤
│    ПАНЕЛЬ БЛОКИРОВОК        │    ПАНЕЛЬ АКТИВНОСТИ                          │
│                             │                                               │
│  src/api.py -> alice [12м]  │  14:32 ▶ #7 alice  Task started              │
│  src/db.py  -> alice [12м]  │  14:31 ✓ #6 bob    Task done                 │
└─────────────────────────────┴───────────────────────────────────────────────┘
```

**Управление TUI** (`swarm tui`): `↑↓` скроллинг, `R` обновить, `D` показать завершённые, `Q` выход

**Цвета статусов:** зелёный — working, жёлтый — waiting, серый — idle, красный — heartbeat > 5 мин

***

## Архитектура

```
swarm CLI (Typer)
├── init.py         — swarm init
├── agent.py        — join, agents, next, done, status, heartbeat
├── task.py         — task add/list/close/assign
├── lock.py         — lock, unlock
├── terminal.py     — terminal launch/status/reconcile/stop
├── monitor.py      — Live-дашборд (Rich)
├── tui.py          — TUI-монитор (Textual)
├── logs.py         — Журнал событий
└── start.py        — Команда старта
        │
   terminal/        — Терминальная оркестрация
   ├── spec.py            — Launch spec (валидация JSON)
   ├── launcher_registry.py — Реестр PowerShell launchers
   ├── layouts.py          — Layout-менеджер (single/mixed/multi-window)
   ├── preflight.py        — Предстартовые проверки
   └── prompt_builder.py   — Генерация bootstrap-промптов
        │
   resources/launchers/   — PowerShell-скрипты запуска (5 CLI × safe/yolo)
        │
   db.py — SQLite WAL, BEGIN IMMEDIATE (атомарный захват задач и блокировок)
        │
   models.py — Agent, Task, FileLock, TaskLogEntry, LaunchSession (dataclasses + enums)
```

**Ключевые решения:**

* **SQLite WAL** — конкурентное чтение без блокировки БД

* **`BEGIN IMMEDIATE`** — атомарный захват задач и файлов

* **Сортировка файлов перед блокировкой** — предотвращение дедлоков

* **Идентификация по** **`--agent`** — несколько экземпляров одного CLI без конфликтов

***

## Структура проекта

```
SWARM/
├── src/swarm/
│   ├── cli.py              # Точка входа CLI (Typer)
│   ├── db.py               # SQLite операции (WAL, CRUD)
│   ├── models.py           # Dataclass-модели
│   ├── utils.py            # Утилиты
│   ├── commands/           # Группы команд
│   │   ├── init.py         # swarm init
│   │   ├── agent.py        # join, agents, next, done, status, heartbeat
│   │   ├── task.py         # task add/list/close/assign
│   │   ├── lock.py         # lock, unlock
│   │   ├── terminal.py     # terminal launch/status/reconcile/stop
│   │   ├── monitor.py      # Live-дашборд (Rich)
│   │   ├── tui.py          # TUI-монитор (Textual)
│   │   ├── logs.py         # Журнал событий
│   │   └── start.py        # Информационная команда
│   ├── terminal/           # Терминальная оркестрация
│   │   ├── spec.py         # Launch spec (валидация, dataclasses)
│   │   ├── launcher_registry.py  # Реестр PowerShell launchers
│   │   ├── layouts.py      # Layout-менеджер (single/mixed/multi-window)
│   │   ├── preflight.py    # Предстартовые проверки
│   │   └── prompt_builder.py  # Генерация bootstrap-промптов
│   └── resources/launchers/  # PowerShell-скрипты (5 CLI × safe/yolo)
├── tests/                  # pytest + CliRunner
├── .claude/                # SKILL.md для Claude Code
├── .codex/                 # SKILL.md для Codex CLI
├── .gemini/                # SKILL.md для Gemini CLI
├── .opencode/              # SKILL.md для OpenCode CLI
├── .qwen/                  # SKILL.md для Qwen CLI
├── USER_GUIDE.md           # Подробное руководство пользователя
└── pyproject.toml          # Конфигурация проекта (hatchling)
```

***

## Разработка

```bash
# Установка с dev-зависимостями
pip install -e ".[dev]"

# Тесты
pytest

# Линтинг
ruff check src/ tests/

# Автоисправление
ruff check --fix src/ tests/
```

| Компонент | Технология         |
| --------- | ------------------ |
| Язык      | Python 3.11+       |
| Сборка    | hatchling          |
| CLI       | Typer              |
| Вывод     | Rich               |
| TUI       | Textual            |
| БД        | SQLite (WAL)       |
| Тесты     | pytest + CliRunner |
| Линтер    | ruff               |

***

## Лицензия

[MIT](LICENSE)

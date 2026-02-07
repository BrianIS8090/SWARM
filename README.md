# SWARM — Multi-Agent Orchestration System

SWARM is a local system for coordinating multiple LLM agents (Claude, Codex, Gemini, OpenCode, Qwen) working in parallel on a shared codebase.

<img width="2529" height="1323" alt="Screenshot 2026-02-06 134233" src="https://github.com/user-attachments/assets/0d05ba34-7886-459f-844b-d2132f9f832c" />

<img width="2330" height="1343" alt="Screenshot 2026-02-06 134238" src="https://github.com/user-attachments/assets/4780894c-ae0e-4302-9efa-831ff8f1802d" />


## Features

- **Unified CLI interface** (`swarm`) for managing agents and tasks
- **Task distribution** with priorities and filtering by role / name / CLI type
- **File locking** to prevent conflicts during parallel editing
- **Live monitor** for real-time status tracking
- **Direct task assignment** to specific agents
- **Fully local operation** — no cloud dependencies

## Quick Start

### 1. Installation

```bash
# From the SWARM directory
pip install -e .'''

2. Project Initialization

Go to your project directory and run:

cd your-project
swarm init

This will create:

swarm.db — database for tasks and agents

SKILLS.md — instructions for LLM agents


3. Creating Tasks

# Simple task
swarm task add --desc "Implement authentication" --priority 1

# Task for a specific role
swarm task add --desc "Design API" --priority 1 --role architect

# Task with dependency (will run after task #1)
swarm task add --desc "Write tests" --priority 2 --depends-on 1

Priorities: 1 (highest) — 5 (lowest)

Roles: architect, developer, tester, devops

CLI types: claude, codex, gemini, opencode, qwen

4. Launching Agents

Open a new terminal for each agent:

# Terminal 1: launch Claude CLI
claude

# In Claude, say:
# "Read SKILLS.md and register via swarm join"

The agent will execute:

swarm join
# It will enter: CLI type, name, role

⚠ IMPORTANT: Agents must use the --agent parameter

After registration, the agent must remember its name and use it in all commands:

# Registration
swarm join --cli codex --name worker1 --role developer

# All subsequent commands — with --agent
swarm next --agent worker1
swarm lock file.py --agent worker1
swarm done --summary "..." --agent worker1

This allows running multiple agents of the same type (e.g., 5 Codex agents) without conflicts.

Repeat this for each agent in a separate terminal.

5. Starting the Monitor

In a separate terminal:

swarm monitor

You will see a live dashboard with 4 panels:

Agents — status of each agent

Tasks — task queue

Locks — which files are locked

Activity — recent events


6. Starting Work

In each agent’s terminal, tell the agent in plain text:

> "Start working. Run swarm next --agent your-name to get a task."



The agent will follow this loop:

1. Get a task (swarm next --agent name)


2. Lock files (swarm lock file --agent name)


3. Perform the work


4. Complete the task (swarm done --agent name)


5. Take the next task



Important: Agents are LLMs in separate terminals. They do not automatically “listen” to the database. You must manually tell each agent to start working.


---

Commands

Leader (Operator) Commands

Command	Description

swarm init	Initialize the SWARM environment
swarm task add	Create a task
swarm task list	Show task list
swarm task assign <ID> --agent <name>	Assign a task to an agent
swarm task close <ID>	Force-close a task
swarm agents	Show agent list
swarm agents --cleanup	Remove inactive agents
swarm monitor	Start live dashboard
swarm tui	TUI monitor with scrolling
swarm logs	Show event log
swarm unlock --force	Force-remove a lock


Agent Commands

All agent commands use the --agent <name> parameter:

Command	Description

swarm join	Register an agent
swarm next --agent name	Get the next task
swarm lock <files> --agent name	Lock files
swarm done --agent name	Complete a task
swarm status --agent name	Show agent status
swarm unlock --agent name	Release own locks


Agent Roles

architect — architecture and design

developer — feature development

tester — testing

devops — infrastructure and deployment


CLI Types

claude — Claude Code

codex — OpenAI Codex CLI

gemini — Gemini CLI

opencode — OpenCode CLI

qwen — Qwen CLI


Project Structure

SWARM/
├── src/swarm/          # Source code
├── tests/              # Tests
├── memory-bank/        # Project context
├── .claude/            # Skills for Claude
├── .codex/             # Skills for Codex
├── .gemini/            # Skills for Gemini
├── .opencode/          # Skills for OpenCode
├── .qwen/              # Skills for Qwen
├── USER_GUIDE.md       # User guide
└── pyproject.toml      # Project configuration

License

MIT



# SWARM — Система оркестрации мультиагентной среды

SWARM — локальная система для координации нескольких LLM-агентов (Claude, Codex, Gemini, OpenCode, Qwen), работающих параллельно над общей кодовой базой.

<img width="2529" height="1323" alt="Снимок экрана 2026-02-06 134233" src="https://github.com/user-attachments/assets/0d05ba34-7886-459f-844b-d2132f9f832c" />

<img width="2330" height="1343" alt="Снимок экрана 2026-02-06 134238" src="https://github.com/user-attachments/assets/4780894c-ae0e-4302-9efa-831ff8f1802d" />


## Возможности

- **Единый CLI-интерфейс** (`swarm`) для управления агентами и задачами
- **Распределение задач** с приоритетами и фильтрацией по роли/имени/типу CLI
- **Блокировка файлов** для предотвращения конфликтов при параллельном редактировании
- **Live-монитор** для отслеживания состояния в реальном времени
- **Назначение задач** конкретным агентам
- **Полностью локальная работа** — без облачных зависимостей

## Быстрый старт

### 1. Установка

```bash
# Из директории SWARM
pip install -e .
```

### 2. Инициализация проекта

Перейдите в папку вашего проекта и выполните:

```bash
cd ваш-проект
swarm init
```

Это создаст:
- `swarm.db` — база данных для задач и агентов
- `SKILLS.md` — инструкция для LLM-агентов

### 3. Создание задач

```bash
# Простая задача
swarm task add --desc "Реализовать авторизацию" --priority 1

# Задача для конкретной роли
swarm task add --desc "Спроектировать API" --priority 1 --role architect

# Задача с зависимостью (выполнится после задачи #1)
swarm task add --desc "Написать тесты" --priority 2 --depends-on 1
```

**Приоритеты:** 1 (наивысший) — 5 (наименьший)

**Роли:** `architect`, `developer`, `tester`, `devops`

**Типы CLI:** `claude`, `codex`, `gemini`, `opencode`, `qwen`

### 4. Запуск агентов

Откройте новый терминал для каждого агента:

```bash
# Терминал 1: Запустите Claude CLI
claude

# В Claude скажите:
# "Прочитай SKILLS.md и зарегистрируйся через swarm join"
```

Агент выполнит:
```bash
swarm join
# Введёт: тип CLI, имя, роль
```

**⚠ ВАЖНО: Агенты должны использовать параметр `--agent`**

После регистрации агент должен **запомнить своё имя** и использовать его во всех командах:

```bash
# Регистрация
swarm join --cli codex --name worker1 --role developer

# Все последующие команды — с --agent
swarm next --agent worker1
swarm lock файл.py --agent worker1
swarm done --summary "..." --agent worker1
```

Это позволяет запускать несколько агентов одного типа (например, 5 Codex) без конфликтов.

Повторите для каждого агента в отдельном терминале.

### 5. Запуск монитора

В отдельном терминале:

```bash
swarm monitor
```

Вы увидите live-дашборд с 4 панелями:
- **Агенты** — статус каждого агента
- **Задачи** — очередь задач
- **Блокировки** — какие файлы заблокированы
- **Активность** — последние события

### 6. Начало работы

**В каждом терминале агента** скажите ему текстом:

> "Начинай работать. Выполни `swarm next --agent твоё-имя` чтобы получить задачу."

Агент выполнит цикл:
1. Получит задачу (`swarm next --agent имя`)
2. Заблокирует файлы (`swarm lock файл --agent имя`)
3. Выполнит работу
4. Завершит задачу (`swarm done --agent имя`)
5. Возьмёт следующую задачу

**Важно:** Агенты — это LLM в отдельных терминалах. Они не "слушают" базу данных автоматически. Вы должны **вручную** сказать каждому агенту начать работу.

---


## Команды

### Команды Лидера (оператора)

| Команда | Описание |
|---------|----------|
| `swarm init` | Инициализировать среду SWARM |
| `swarm task add` | Создать задачу |
| `swarm task list` | Показать список задач |
| `swarm task assign <ID> --agent <имя>` | Назначить задачу агенту |
| `swarm task close <ID>` | Принудительно закрыть задачу |
| `swarm agents` | Показать список агентов |
| `swarm agents --cleanup` | Удалить неактивных агентов |
| `swarm monitor` | Запустить live-дашборд |
| `swarm tui` | TUI-монитор со скроллингом |
| `swarm logs` | Показать журнал событий |
| `swarm unlock --force` | Принудительно снять блокировку |

### Команды агента

Все команды агента используют параметр `--agent <имя>`:

| Команда | Описание |
|---------|----------|
| `swarm join` | Зарегистрировать агента |
| `swarm next --agent имя` | Получить следующую задачу |
| `swarm lock <файлы> --agent имя` | Заблокировать файлы |
| `swarm done --agent имя` | Завершить задачу |
| `swarm status --agent имя` | Показать статус агента |
| `swarm unlock --agent имя` | Снять свои блокировки |

## Роли агентов

- `architect` — архитектура и проектирование
- `developer` — разработка функциональности
- `tester` — тестирование
- `devops` — инфраструктура и деплой

## Типы CLI

- `claude` — Claude Code
- `codex` — OpenAI Codex CLI
- `gemini` — Gemini CLI
- `opencode` — OpenCode CLI
- `qwen` — Qwen CLI

## Структура проекта

```
SWARM/
├── src/swarm/          # Исходный код
├── tests/              # Тесты
├── memory-bank/        # Контекст проекта
├── .claude/            # Скиллы для Claude
├── .codex/             # Скиллы для Codex
├── .gemini/            # Скиллы для Gemini
├── .opencode/          # Скиллы для OpenCode
├── .qwen/              # Скиллы для Qwen
├── USER_GUIDE.md       # Руководство пользователя
└── pyproject.toml      # Конфигурация проекта
```

## Лицензия

MIT
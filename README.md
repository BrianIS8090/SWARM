
Файл 1: README.md (Основной, английский)
Создай файл README.md и вставь туда этот код:
<div align="center">
  <a href="README_RU.md">
    <img src="https://img.shields.io/badge/Lang-Russian-blue.svg" alt="Russian">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/Lang-English-red.svg" alt="English">
  </a>
</div>

---

# SWARM — Multi-Agent Orchestration System

SWARM is a local system for coordinating multiple LLM agents (Claude, Codex, Gemini, OpenCode, Qwen) working in parallel on a shared codebase.

<img width="2529" height="1323" alt="Screen Shot 2026-02-06 134233" src="https://github.com/user-attachments/assets/0d05ba34-7886-459f-844b-d2132f9f832c" />

<img width="2330" height="1343" alt="Screen Shot 2026-02-06 134238" src="https://github.com/user-attachments/assets/4780894c-ae0e-4302-9efa-831ff8f1802d" />

## Features

- **Unified CLI Interface** (`swarm`) for managing agents and tasks.
- **Task Distribution** with priorities and filtering by role/name/CLI type.
- **File Locking** to prevent conflicts during parallel editing.
- **Live Monitor** for real-time status tracking.
- **Task Assignment** to specific agents.
- **Fully Local Operation** — no cloud dependencies.

## Quick Start

### 1. Installation

```bash
# From the SWARM directory
pip install -e .

2. Project Initialization
Navigate to your project folder and run:
cd your-project
swarm init

This creates:
 * swarm.db — database for tasks and agents.
 * SKILLS.md — instructions/skills for the LLM agents.
3. Creating Tasks
# Simple task
swarm task add --desc "Implement authorization" --priority 1

# Task for a specific role
swarm task add --desc "Design API" --priority 1 --role architect

# Task with a dependency (runs only after task #1 is complete)
swarm task add --desc "Write tests" --priority 2 --depends-on 1

Priorities: 1 (Highest) — 5 (Lowest)
Roles: architect, developer, tester, devops
CLI Types: claude, codex, gemini, opencode, qwen
4. Launching Agents
Open a new terminal window for each agent you want to run:
# Terminal 1: Launch Claude CLI
claude

# Inside Claude, say:
# "Read SKILLS.md and register using swarm join"

The agent will execute:
swarm join
# It will enter: CLI type, name, role

⚠ IMPORTANT: Agents must use the --agent parameter
After registration, the agent must remember its name and use it in all subsequent commands:
# Registration
swarm join --cli codex --name worker1 --role developer

# All subsequent commands — must include --agent
swarm next --agent worker1
swarm lock file.py --agent worker1
swarm done --summary "..." --agent worker1

This allows you to run multiple agents of the same type (e.g., 5 Codex instances) without conflicts.
Repeat this process for each agent in a separate terminal.
5. Launching the Monitor
In a separate terminal:
swarm monitor

You will see a live dashboard with 4 panels:
 * Agents — status of each agent.
 * Tasks — the task queue.
 * Locks — currently locked files.
 * Activity — recent events log.
6. Starting Work
In each agent's terminal, tell them via text prompt:
> "Start working. Run swarm next --agent your-name to get a task."
> 
The agent will enter a loop:
 * Get a task (swarm next --agent name)
 * Lock files (swarm lock file --agent name)
 * Perform the work
 * Complete the task (swarm done --agent name)
 * Pick up the next task
Note: Agents are LLMs running in separate terminals. They do not "listen" to the database automatically. You must manually prompt each agent to begin the workflow.
Commands
Leader (Operator) Commands
| Command | Description |
|---|---|
| swarm init | Initialize the SWARM environment |
| swarm task add | Create a new task |
| swarm task list | Show the list of tasks |
| swarm task assign <ID> --agent <name> | Assign a task to a specific agent |
| swarm task close <ID> | Force close a task |
| swarm agents | Show the list of agents |
| swarm agents --cleanup | Remove inactive agents |
| swarm monitor | Launch the live dashboard |
| swarm tui | Launch TUI monitor with scrolling |
| swarm logs | Show the event log |
| swarm unlock --force | Force release a file lock |
Agent Commands
All agent commands require the --agent <name> parameter:
| Command | Description |
|---|---|
| swarm join | Register the agent |
| swarm next --agent name | Get the next available task |
| swarm lock <files> --agent name | Lock files for editing |
| swarm done --agent name | Complete the current task |
| swarm status --agent name | Show agent status |
| swarm unlock --agent name | Release own locks |
Agent Roles
 * architect — Architecture and design
 * developer — Functionality development
 * tester — Testing and QA
 * devops — Infrastructure and deployment
Supported CLI Types
 * claude — Claude Code
 * codex — OpenAI Codex CLI
 * gemini — Gemini CLI
 * opencode — OpenCode CLI
 * qwen — Qwen CLI
Project Structure
SWARM/
├── src/swarm/          # Source code
├── tests/              # Tests
├── memory-bank/        # Project context
├── .claude/            # Skills/Instructions for Claude
├── .codex/             # Skills/Instructions for Codex
├── .gemini/            # Skills/Instructions for Gemini
├── .opencode/          # Skills/Instructions for OpenCode
├── .qwen/              # Skills/Instructions for Qwen
├── USER_GUIDE.md       # User Guide
└── pyproject.toml      # Project configuration

License
MIT

---

### Файл 2: `README_RU.md` (Русская версия)
Создай файл `README_RU.md` и вставь туда этот код:

```markdown
<div align="center">
  <a href="README_RU.md">
    <img src="https://img.shields.io/badge/Lang-Russian-blue.svg" alt="Russian">
  </a>
  <a href="README.md">
    <img src="https://img.shields.io/badge/Lang-English-red.svg" alt="English">
  </a>
</div>

---

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

2. Инициализация проекта
Перейдите в папку вашего проекта и выполните:
cd ваш-проект
swarm init

Это создаст:
 * swarm.db — база данных для задач и агентов
 * SKILLS.md — инструкция для LLM-агентов
3. Создание задач
# Простая задача
swarm task add --desc "Реализовать авторизацию" --priority 1

# Задача для конкретной роли
swarm task add --desc "Спроектировать API" --priority 1 --role architect

# Задача с зависимостью (выполнится после задачи #1)
swarm task add --desc "Написать тесты" --priority 2 --depends-on 1

Приоритеты: 1 (наивысший) — 5 (наименьший)
Роли: architect, developer, tester, devops
Типы CLI: claude, codex, gemini, opencode, qwen
4. Запуск агентов
Откройте новый терминал для каждого агента:
# Терминал 1: Запустите Claude CLI
claude

# В Claude скажите:
# "Прочитай SKILLS.md и зарегистрируйся через swarm join"

Агент выполнит:
swarm join
# Введёт: тип CLI, имя, роль

⚠ ВАЖНО: Агенты должны использовать параметр --agent
После регистрации агент должен запомнить своё имя и использовать его во всех командах:
# Регистрация
swarm join --cli codex --name worker1 --role developer

# Все последующие команды — с --agent
swarm next --agent worker1
swarm lock файл.py --agent worker1
swarm done --summary "..." --agent worker1

Это позволяет запускать несколько агентов одного типа (например, 5 Codex) без конфликтов.
Повторите для каждого агента в отдельном терминале.
5. Запуск монитора
В отдельном терминале:
swarm monitor

Вы увидите live-дашборд с 4 панелями:
 * Агенты — статус каждого агента
 * Задачи — очередь задач
 * Блокировки — какие файлы заблокированы
 * Активность — последние события
6. Начало работы
В каждом терминале агента скажите ему текстом:
> "Начинай работать. Выполни swarm next --agent твоё-имя чтобы получить задачу."
> 
Агент выполнит цикл:
 * Получит задачу (swarm next --agent имя)
 * Заблокирует файлы (swarm lock файл --agent имя)
 * Выполнит работу
 * Завершит задачу (swarm done --agent имя)
 * Возьмёт следующую задачу
Важно: Агенты — это LLM в отдельных терминалах. Они не "слушают" базу данных автоматически. Вы должны вручную сказать каждому агенту начать работу.
Команды
Команды Лидера (оператора)
| Команда | Описание |
|---|---|
| swarm init | Инициализировать среду SWARM |
| swarm task add | Создать задачу |
| swarm task list | Показать список задач |
| swarm task assign <ID> --agent <имя> | Назначить задачу агенту |
| swarm task close <ID> | Принудительно закрыть задачу |
| swarm agents | Показать список агентов |
| swarm agents --cleanup | Удалить неактивных агентов |
| swarm monitor | Запустить live-дашборд |
| swarm tui | TUI-монитор со скроллингом |
| swarm logs | Показать журнал событий |
| swarm unlock --force | Принудительно снять блокировку |
Команды агента
Все команды агента используют параметр --agent <имя>:
| Команда | Описание |
|---|---|
| swarm join | Зарегистрировать агента |
| swarm next --agent имя | Получить следующую задачу |
| swarm lock <файлы> --agent имя | Заблокировать файлы |
| swarm done --agent имя | Завершить задачу |
| swarm status --agent имя | Показать статус агента |
| swarm unlock --agent имя | Снять свои блокировки |
Роли агентов
 * architect — архитектура и проектирование
 * developer — разработка функциональности
 * tester — тестирование
 * devops — инфраструктура и деплой
Типы CLI
 * claude — Claude Code
 * codex — OpenAI Codex CLI
 * gemini — Gemini CLI
 * opencode — OpenCode CLI
 * qwen — Qwen CLI
Структура проекта
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

Лицензия
MIT


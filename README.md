# SWARM — Система оркестрации мультиагентной среды

SWARM — локальная система для координации нескольких LLM-агентов (Claude, Codex, Gemini, OpenCode, Qwen), работающих параллельно над общей кодовой базой.

## Возможности

- **Единый CLI-интерфейс** (`swarm`) для управления агентами и задачами
- **Распределение задач** с приоритетами и фильтрацией по роли/имени/типу CLI
- **Блокировка файлов** для предотвращения конфликтов при параллельном редактировании
- **Live-монитор** для отслеживания состояния в реальном времени
- **Назначение задач** конкретным агентам
- **Полностью локальная работа** — без облачных зависимостей

## Установка

```bash
pip install -e .
```

Или из исходников:

```bash
git clone https://github.com/your-repo/swarm.git
cd swarm
pip install -e .
```

## Быстрый старт

### 1. Инициализация

```bash
cd your-project
swarm init
```

### 2. Создание задач

```bash
swarm task add --desc "Реализовать REST API для пользователей" --priority 1
swarm task add --desc "Написать юнит-тесты" --priority 2 --role tester
swarm task add --desc "Спроектировать архитектуру" --role architect
```

### 3. Регистрация агента

В новом терминале запустите CLI агента (например, `claude`) и выполните:

```bash
swarm join
```

### 4. Работа агента

```bash
swarm next              # Получить задачу
swarm lock src/api.py   # Заблокировать файлы
# ... выполнить работу ...
swarm done --summary "Реализован UserController с CRUD-операциями"
swarm next              # Следующая задача
```

### 5. Мониторинг

```bash
swarm monitor
```

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

# План исправлений SWARM (v0.4.x → v0.5)

Документ фиксирует технический долг, найденный при ревизии проекта (июль 2026), и порядок его устранения. Каждый пункт содержит проблему, конкретные шаги и критерии приёмки. Пункты сгруппированы в три этапа — их можно выполнять последовательными небольшими PR.

## Сводная таблица

| # | Проблема | Приоритет | Оценка | Этап |
|---|----------|-----------|--------|------|
| П1 | Нет CI — линт и тесты не запускаются автоматически | Критический | 0.5 дня | 1 |
| П2 | Тест с патчем `os.name` роняет pytest (INTERNALERROR) | Критический | 0.5 дня | 1 |
| П3 | Ошибки ruff; pre-commit объявлен, но не настроен | Высокий | 0.5 дня | 1 |
| П4 | `graphify-out/` закоммичен, содержит локальные пути разработчика | Высокий | 0.5 дня | 1 |
| П5 | Версия задублирована: `pyproject.toml` и `version.json` | Средний | 0.5 дня | 1 |
| П6 | Дублирование кода: heartbeat/статусы ×4, резолв агента ×3 | Высокий | 1 день | 2 |
| П7 | Шаблоны SKILL.md зашиты строками в `init.py` (~450 строк) | Средний | 1 день | 2 |
| П8 | Смешение отступов 2/4 пробела, нет автоформаттера | Средний | 0.5 дня | 2 |
| П9 | `terminal/` и UI-слой полностью без тестов | Высокий | 3–4 дня | 3 |
| П10 | `launch_command` ~165 строк, монолит | Средний | 1 день | 3 |

---

## Этап 1. Инфраструктура качества (цель: зелёный CI)

### П1. GitHub Actions CI

**Проблема.** В dev-зависимостях объявлены ruff, pytest и pre-commit, но нет ни `.github/workflows`, ни какой-либо другой автоматизации. Заявленные quality-гейты ничем не обеспечены.

**Шаги.**
1. Создать `.github/workflows/ci.yml`:
   - матрица: `ubuntu-latest` и `windows-latest` × Python 3.11, 3.12;
   - шаги: `pip install -e ".[dev]"` → `ruff check src/ tests/` → `pytest`;
   - запуск на `push` в `main` и на `pull_request`.
2. Windows-задание особенно важно: терминальный слой (`swarm terminal`, `swarm path`) исполняется только там.
3. Добавить бейдж статуса CI в README.

**Критерии приёмки.** Workflow зелёный на обеих ОС; PR без зелёного CI не мержится (branch protection — настраивается владельцем репозитория).

**Зависимости.** Требует П2 и П3 — сейчас и тесты, и линт красные.

### П2. Починка теста с патчем `os.name`

**Проблема.** `tests/test_terminal_cmd.py:77` выполняет `monkeypatch.setattr("os.name", "nt")`. Пока патч активен, любой вызов `pathlib.Path(...)` на Linux бросает `NotImplementedError: cannot instantiate 'WindowsPath'`. В результате тест падает, pytest не может отрисовать ошибку и завершает прогон INTERNALERROR (в т.ч. ломается очистка tmp-директорий).

**Шаги.**
1. В `src/swarm/commands/terminal.py` добавить шов для платформы:
   ```python
   def _is_windows() -> bool:
       return os.name == "nt"
   ```
   и заменить прямые проверки `os.name == "nt"` (например, `terminal.py:340`) на вызов хелпера.
2. В тестах патчить `terminal_cmd._is_windows` вместо глобального `os.name` (`tests/test_terminal_cmd.py:77`, `:128`).
3. Проверить остальной код на прямые сравнения `os.name` / `platform.system()` и решить, где нужен тот же шов (как минимум `db.is_process_alive` уже мокается корректно — не трогать без необходимости).

**Критерии приёмки.** `python -m pytest` завершается без INTERNALERROR на Linux и Windows; тест `TestStopCommandFallback` проходит в изоляции (`pytest tests/test_terminal_cmd.py -q`).

### П3. Чистый ruff и pre-commit

**Проблема.** `ruff check src/ tests/` находит 3 ошибки (`SIM105` в `path_cmd.py:77`, `I001` в `tui.py:7` и ещё одна). `pre-commit` в dev-зависимостях, но `.pre-commit-config.yaml` отсутствует.

**Шаги.**
1. `ruff check --fix src/ tests/`, оставшееся поправить руками.
2. Убрать из `except (FileNotFoundError, KeyError, json.JSONDecodeError, Exception)` в `utils.py:50` лишний перечень — оставить осмысленный набор исключений без голого `Exception`.
3. Добавить `.pre-commit-config.yaml` с хуками `ruff` (check + format, см. П8) и базовыми (`trailing-whitespace`, `end-of-file-fixer` — с оглядкой на то, что W291/W293 сейчас в ignore).

**Критерии приёмки.** `ruff check` — 0 ошибок; `pre-commit run --all-files` зелёный.

### П4. Гигиена репозитория: `graphify-out/`

**Проблема.** В git закоммичен 91 файл сгенерированного вывода code-graph-инструмента (`graphify-out/`): `graph.json`, `cache/{ast,semantic}/*.json` и т.д. `manifest.json` содержит локальные пути разработчика (`C:\Users\Brian\Downloads\SWARM\...`).

**Шаги.**
1. Добавить в `.gitignore`: `graphify-out/`, а заодно `.swarm/`, `swarm.db*` (включая `-wal`/`-shm`), если ещё не игнорируются.
2. `git rm -r --cached graphify-out/` и закоммитить удаление.
3. Проверить, что README не ссылается на файлы из `graphify-out` как на обязательные (при необходимости — поправить раздел).

**Критерии приёмки.** `git ls-files | grep graphify-out` пусто; свежий `swarm init` + запуск агентов не оставляют неигнорируемых файлов в `git status`.

### П5. Единый источник версии

**Проблема.** Версия существует в трёх местах: `pyproject.toml:7` (`0.4.0`), `src/swarm/version.json` (читается `utils.get_version()` в рантайме) и `src/swarm/__init__.py:__version__`. Они неизбежно разъедутся.

**Шаги (вариант А, минимальный — рекомендуется).**
1. Оставить источником `version.json` (там же codename и release_date, которые показывает CLI).
2. В `pyproject.toml` переключиться на динамическую версию hatchling:
   ```toml
   [project]
   dynamic = ["version"]

   [tool.hatch.version]
   path = "src/swarm/version.json"
   pattern = '"version":\s*"(?P<version>[^"]+)"'
   ```
3. `__init__.__version__` получать через `utils.get_version()` либо удалить, оставив одну точку чтения.

**Критерии приёмки.** Обновление версии требует правки ровно одного файла; `pip install -e .` и `swarm --version`-подобный вывод показывают одно и то же значение; тест на согласованность.

---

## Этап 2. Устранение дублирования и стиль

### П6. Общий модуль форматирования и резолва агентов

**Проблема.** Логика «секунды с последнего heartbeat → строка `5с/3м/1ч` + цвет/иконка статуса» скопирована в четырёх местах: `agent.py:158-199`, `monitor.py:54-96`, `logs.py:62-83`, `tui.py:39-113`. Резолв агента по имени переизобретён в `logs.py:36-43` и `start.py:41-49` вместо `db.get_agent_by_name` / `common._check_agent`.

**Шаги.**
1. Создать `src/swarm/format.py`:
   - `format_heartbeat_age(last_heartbeat: datetime, now: datetime | None = None) -> tuple[str, str]` — текст и стиль;
   - `AGENT_STATUS_STYLE: dict[AgentStatus, tuple[str, str]]` (иконка, цвет);
   - `TASK_STATUS_STYLE: dict[TaskStatus, tuple[str, str]]`.
2. Перевести все четыре потребителя на общий модуль; расхождения между копиями (если найдутся) зафиксировать сознательно.
3. `logs.py` и `start.py` перевести на `get_agent_by_name`.
4. Покрыть `format.py` unit-тестами (границы: <60с, минуты, часы, порог «красноты» 300с).

**Критерии приёмки.** `grep` по репозиторию не находит повторной реализации форматирования heartbeat; вывод `agents`/`monitor`/`tui`/`logs` не изменился визуально (или изменения описаны в PR).

### П7. Вынос SKILL-шаблонов из `init.py`

**Проблема.** `init.py` — 611 строк, из них ~450 — два f-string-шаблона (`get_orchestrator_skill_template`, `get_skill_template`, строки 22–451), дублирующие содержимое `.claude/skills/`. Три источника правды дрейфуют.

**Шаги.**
1. Создать `src/swarm/resources/skills/orchestrator.md` и `agent.md`; параметры подставлять через `str.format` (или `string.Template`, чтобы не экранировать фигурные скобки в markdown).
2. Читать через `importlib.resources.files("swarm.resources") / ...`; добавить каталог в `[tool.hatch.build.targets.wheel]` artifacts при необходимости.
3. `swarm init` продолжает раскладывать файлы по `.claude/skills/...` и т.п. — поведение не меняется.
4. Решить судьбу копий в репозитории (`.claude/skills/`, `.gemini/skills/`): либо генерировать их из тех же ресурсов (скрипт/pre-commit), либо задокументировать, что канонический источник — `src/swarm/resources/`.

**Критерии приёмки.** `init.py` < 200 строк; сгенерированные `swarm init` файлы байт-в-байт совпадают с прежними (снять снапшот до рефакторинга и сравнить в тесте).

### П8. Единый стиль отступов и автоформаттер

**Проблема.** CLAUDE.md декларирует отступ 2 пробела, но так написаны только `utils.py`, `common.py`, `tui.py`, `terminal/layouts.py` и часть `preflight.py`; остальной код — 4 пробела. Автоформаттера нет.

**Шаги.**
1. Принять решение: стандартные 4 пробела (рекомендуется — это PEP 8, дефолт ruff format, и большинство кода уже такое).
2. Прогнать `ruff format src/ tests/`, зафиксировать одним отдельным коммитом «formatting only» (удобно для `git blame --ignore-rev`).
3. Обновить CLAUDE.md и AGENTS.md (раздел «Конвенции»: отступ 4 пробела).
4. Включить `ruff format --check` в CI и pre-commit.

**Критерии приёмки.** `ruff format --check` зелёный в CI; конвенция в CLAUDE.md соответствует реальности.

---

## Этап 3. Покрытие рискованного кода

### П9. Тесты терминального и UI-слоя

**Проблема.** Полностью без тестов: `terminal/layouts.py`, `terminal/preflight.py`, `terminal/prompt_builder.py`, `terminal/launcher_registry.py`, `commands/monitor.py`, `commands/tui.py`, `commands/logs.py`, `commands/start.py`, `commands/init.py`, `commands/path_cmd.py`. При этом terminal-launch — самый побочно-эффектный код проекта, а кодовое имя релиза 0.4.0 — «Reliability & Testing».

**Шаги (по убыванию ценности).**
1. `layouts.py` — чистая функция построения аргументов `wt`: снапшот-тесты для `single`/`mixed`/`multi-window`, 1–8 агентов, границы панелей.
2. `preflight.py` — тесты каждого чека с моками `shutil.which`/`Path.exists`/БД.
3. `prompt_builder.py`, `launcher_registry.py` — тривиальные unit-тесты (вход → выход).
4. `logs.py`, `start.py` — CLI-тесты через `CliRunner` по образцу `test_cli.py`.
5. `init.py` — тест на состав созданных файлов и идемпотентность повторного запуска.
6. `monitor.py`/`tui.py` — вынести построение таблиц/панелей в чистые функции «данные → renderable» и тестировать их; сам event-loop не тестировать. Для `tui.py` опционально `textual.pilot`.
7. `path_cmd.py` — тесты только под `sys.platform == "win32"` (skipif), запускаются в Windows-задании CI.
8. Включить `pytest-cov` в CI с порогом (стартово ~70% total, поднимать по мере закрытия долга).

**Критерии приёмки.** Ни одного модуля с нулевым покрытием; порог покрытия зафиксирован в CI.

### П10. Декомпозиция `terminal.launch_command`

**Проблема.** `terminal.py:75-241` — функция ~165 строк: загрузка spec, preflight, создание сессии, подтверждение, сборка промптов, вставка агентов в БД, запуск layout, реконсиляция статусов, вывод панели, обработка `--exclude-cli`.

**Шаги.**
1. Разбить на этапы с чистыми сигнатурами:
   - `_load_and_validate_spec(path) -> LaunchSpec`
   - `_plan_session(spec, exclude_cli) -> LaunchPlan` (что запускаем, что исключено)
   - `_persist_session(plan) -> LaunchSession`
   - `_execute_launch(plan, dry_run) -> LaunchResult`
   - `_report(result)` — весь Rich-вывод.
2. `launch_command` остаётся тонким конвейером + обработкой `--yes`/`--dry-run`.
3. На каждый этап — unit-тесты (это одновременно закрывает часть П9).

**Критерии приёмки.** `launch_command` < 50 строк; поведение CLI не изменилось (существующие тесты `test_terminal_cmd.py` зелёные без правок ожиданий).

---

## Порядок выполнения и связи

```
Этап 1: П2 → П3 → П1 (CI зелёный) ; параллельно П4, П5
Этап 2: П6, П7, П8 (П8 — отдельным formatting-коммитом после П6/П7)
Этап 3: П10 → П9 (декомпозиция упрощает тестирование)
```

Каждый пункт — отдельный небольшой PR. Этап 1 целиком укладывается в один день работы и сразу даёт защитную сетку для этапов 2–3 и для фич из DESIGN_FEATURES.md.

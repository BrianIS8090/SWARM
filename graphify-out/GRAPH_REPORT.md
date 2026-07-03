# Graph Report - C:\Users\Brian\Downloads\SWARM  (2026-05-07)

## Corpus Check
- Corpus is ~35,964 words - fits in a single context window. You may not need a graph.

## Summary
- 1097 nodes · 2027 edges · 114 communities (69 shown, 45 thin omitted)
- Extraction: 63% EXTRACTED · 37% INFERRED · 0% AMBIGUOUS · INFERRED: 753 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Agent Operations & Database Tasks|Agent Operations & Database Tasks]]
- [[_COMMUNITY_Terminal Spec Validation|Terminal Spec Validation]]
- [[_COMMUNITY_Task Assignment & Locks|Task Assignment & Locks]]
- [[_COMMUNITY_Models & Enums|Models & Enums]]
- [[_COMMUNITY_TUI Formatting & Status|TUI Formatting & Status]]
- [[_COMMUNITY_Database File Locking|Database File Locking]]
- [[_COMMUNITY_Terminal Launch Commands|Terminal Launch Commands]]
- [[_COMMUNITY_Task Logging Commands|Task Logging Commands]]
- [[_COMMUNITY_TUI Overview Panels|TUI Overview Panels]]
- [[_COMMUNITY_Tokens & Shell Detection|Tokens & Shell Detection]]
- [[_COMMUNITY_Edge Cases Tests|Edge Cases Tests]]
- [[_COMMUNITY_Monitor Dashboard|Monitor Dashboard]]
- [[_COMMUNITY_Agent CLI Commands|Agent CLI Commands]]
- [[_COMMUNITY_Init & Skill Templates|Init & Skill Templates]]
- [[_COMMUNITY_Models Tests|Models Tests]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]
- [[_COMMUNITY_Community 110|Community 110]]
- [[_COMMUNITY_Community 111|Community 111]]
- [[_COMMUNITY_Community 112|Community 112]]
- [[_COMMUNITY_Community 113|Community 113]]

## God Nodes (most connected - your core abstractions)
1. `register_agent()` - 56 edges
2. `create_task()` - 54 edges
3. `TaskStatus` - 45 edges
4. `AgentStatus` - 42 edges
5. `get_connection()` - 37 edges
6. `EventType` - 37 edges
7. `LaunchSessionStatus` - 34 edges
8. `LaunchRegistrationStatus` - 34 edges
9. `_validate_spec()` - 32 edges
10. `SwarmTUI` - 31 edges

## Surprising Connections (you probably didn't know these)
- `launch_layout` --implements--> `Terminal Orchestration`  [INFERRED]
  src/swarm/terminal/layouts.py → USER_GUIDE.md
- `LaunchSpec` --implements--> `Launch Spec`  [INFERRED]
  src/swarm/terminal/spec.py → USER_GUIDE.md
- `temp_db()` --calls--> `init_database()`  [INFERRED]
  tests/conftest.py → src/swarm/db.py
- `sample_agent()` --calls--> `register_agent()`  [INFERRED]
  tests/conftest.py → src/swarm/db.py
- `sample_task()` --calls--> `create_task()`  [INFERRED]
  tests/conftest.py → src/swarm/db.py

## Communities (114 total, 45 thin omitted)

### Community 0 - "Agent Operations & Database Tasks"
Cohesion: 0.05
Nodes (73): agents_command, done_command, heartbeat_command, join_command, next_command, status_command, app, _check_agent (+65 more)

### Community 1 - "Terminal Spec Validation"
Cohesion: 0.07
Nodes (29): _validate_spec(), _make_valid_spec(), Негативные тесты валидации spec — все ветви ошибок., Неверная версия spec вызывает ValueError., Отсутствующая версия вызывает ValueError., Пустой working_directory вызывает ValueError., Отсутствующий working_directory вызывает ValueError., Нестроковый working_directory вызывает ValueError. (+21 more)

### Community 2 - "Task Assignment & Locks"
Cohesion: 0.06
Nodes (33): assign_task_to_agent(), claim_next_task(), complete_task(), get_agent_by_session(), Регистрирует нового агента. m-2: атомарно с логом. m-9: валидация имени., Получает агента по токену сессии., Назначает задачу конкретному агенту (устанавливает target_name)., Атомарно захватывает следующую подходящую задачу для агента. (+25 more)

### Community 3 - "Models & Enums"
Cohesion: 0.1
Nodes (47): Enum, AgentStatus, EventType, LaunchRegistrationStatus, LaunchSessionStatus, Типы событий для лога., Статусы сессии запуска терминалов., Статусы регистрации агента внутри launch-сессии. (+39 more)

### Community 4 - "TUI Formatting & Status"
Cohesion: 0.06
Nodes (33): _fmt_heartbeat(), Форматирует детальную информацию об агенте., Форматирует heartbeat: '5с', '3м', '1ч'., Показывает детали при навигации по таблице., str, get_launch_sessions(), init_database(), is_process_alive() (+25 more)

### Community 5 - "Database File Locking"
Cohesion: 0.08
Nodes (28): create_task(), get_all_locks(), get_file_lock(), Создаёт новую задачу. m-10: проверка цикличных зависимостей.      КРИТ-4: BEGI, Пытается захватить блокировку. C-1: BEGIN IMMEDIATE для атомарности., Получает информацию о блокировке файла., Возвращает все активные блокировки., Снимает блокировку с файла. (+20 more)

### Community 6 - "Terminal Launch Commands"
Cohesion: 0.07
Nodes (39): Показывает активные launch-сессии и состояние регистрации., Останавливает launch-сессию и закрывает терминалы агентов., Сверяет launch session с фактически зарегистрированными агентами., reconcile_command(), status_command(), stop_command(), add_launch_session_agent(), create_launch_session() (+31 more)

### Community 7 - "Task Logging Commands"
Cohesion: 0.07
Nodes (24): add_command(), assign_command(), Назначает задачу конкретному агенту.          После назначения только этот аге, Создаёт новую задачу в очереди., force_close_task(), get_recent_events(), get_task(), log_event() (+16 more)

### Community 8 - "TUI Overview Panels"
Cohesion: 0.12
Nodes (23): OverviewActivityPanel, OverviewAgentsPanel, OverviewLocksPanel, OverviewTasksPanel, TUI-монитор SWARM на базе Textual.  Презентабельный интерфейс с 6 вкладками и, Верхняя полоса со счётчиками и прогрессом., Компактная таблица агентов для обзора., Компактная таблица задач для обзора. (+15 more)

### Community 9 - "Tokens & Shell Detection"
Cohesion: 0.07
Nodes (23): _detect_shell_command(), load_session_token(), Определяет команду установки env-переменной для текущей оболочки (m-7)., Сохраняет токен сессии. C-5: токен не в env. M-8: права 0600., Загружает токен сессии из файла или env., save_session_token(), Тесты управления агентами., Проверяет получение текущего агента. (+15 more)

### Community 10 - "Edge Cases Tests"
Cohesion: 0.06
Nodes (21): Тесты граничных случаев для lock, task и agents., unlock --file X без --agent и без env vars выдаёт ошибку с подсказкой., Повторная блокировка того же файла через CLI — идемпотентна., Граничные случаи задач через CLI., Приоритет 0 — невалидный, должна быть ошибка., Приоритет 6 — невалидный, должна быть ошибка., Приоритеты 1 и 5 — граничные допустимые значения., Зависимость от несуществующей задачи вызывает ошибку. (+13 more)

### Community 11 - "Monitor Dashboard"
Cohesion: 0.08
Nodes (26): create_activity_panel(), create_agents_panel(), create_dashboard(), create_locks_panel(), create_tasks_panel(), monitor_command(), Команда swarm monitor.  Live-дашборд с 4 панелями: - Панель агентов - Панель, Создаёт панель задач. (+18 more)

### Community 12 - "Agent CLI Commands"
Cohesion: 0.09
Nodes (26): done_command(), heartbeat_command(), join_command(), next_command(), Команды управления агентами.  - swarm join — регистрация агента - swarm agent, Получает следующую задачу для агента., Завершает текущую задачу агента., Показывает статус текущего агента. (+18 more)

### Community 13 - "Init & Skill Templates"
Cohesion: 0.1
Nodes (18): get_orchestrator_skill_template(), get_skill_template(), init_command(), Модуль команд SWARM CLI.  Содержит реализации всех CLI-команд: - init — иници, Генерирует SKILL.md для оркестратора., Генерирует SKILL.md для конкретного типа агента., Инициализирует среду SWARM.      Создаёт swarm.db и папки со SKILL.md для кажд, get_version() (+10 more)

### Community 14 - "Models Tests"
Cohesion: 0.1
Nodes (17): _agent_row(), _file_lock_row(), _launch_session_agent_row(), Тесты моделей данных SWARM.  Проверяет безопасный парсинг enum-значений из БД че, Возвращает словарь, имитирующий строку из таблицы launch_session_agents., Тесты десериализации Agent из строки БД., Валидный статус агента парсится корректно., Неизвестный статус агента не бросает ValueError. (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.16
Nodes (16): LaunchAgentSpec, LayoutSpec, load_launch_spec(), Валидация и загрузка launch spec для swarm terminal., Сохраняет launch spec в JSON-файл., Загружает и валидирует launch spec из JSON-файла., Описание layout для запуска терминалов., Описание одного агента в launch spec. (+8 more)

### Community 16 - "Community 16"
Cohesion: 0.1
Nodes (15): agents_command(), Показывает список зарегистрированных агентов., Сигнализирует агентам о начале работы.          Это информационная команда — а, start_command(), cleanup_dead_agents(), get_all_agents(), Возвращает список всех зарегистрированных агентов., Удаляет неактивных агентов. M-1: освобождает задачи/блокировки. m-4: UTC. (+7 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (15): from_row(), LaunchSession, LaunchSessionAgent, _parse_dt(), Модели данных для SWARM.  Dataclass-модели для агентов, задач, блокировок и собы, Сессия запуска терминальных агентов., Агент, входящий в launch-сессию., Безопасное создание enum из значения БД.      При неизвестном значении возвращае (+7 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (5): Презентабельный TUI-монитор SWARM., Загружает данные из БД один раз и обновляет все виджеты., Обновляет таблицу активных задач (фильтр done по клавише f)., Обновляет полный лог активности (последние 100 записей из БД)., SwarmTUI

### Community 19 - "Community 19"
Cohesion: 0.19
Nodes (15): get_launcher_path(), get_launchers_dir(), Реестр PowerShell launchers для CLI-агентов., Возвращает путь к launcher-скрипту по CLI и режиму., Возвращает директорию встроенных launchers., _agent_sort_key(), _build_mixed_window_args(), _chunks() (+7 more)

### Community 20 - "Community 20"
Cohesion: 0.16
Nodes (15): _auto_layout_mode(), launch_command(), _print_excluded_command(), _print_launch_plan(), Команды терминальной оркестрации: swarm terminal ..., Сохраняет excluded-агентов в отдельный spec и выводит команду для пользователя., Определяет layout mode по количеству агентов., Запускает новую launch-сессию на основе launch spec. (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (15): _broadcast_environment_change(), _contains_path_entry(), _get_user_scripts_dir(), path_command(), Команда swarm path.  Управляет добавлением пользовательского каталога Python S, Возвращает каталог Scripts для пользовательской схемы установки Python., Разбивает PATH на элементы без пустых сегментов., Проверяет наличие target в PATH без учёта регистра и слэшей. (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (8): Тесты команд агентов., Проверяет регистрацию агента., Проверяет пустой список агентов., Проверяет список с агентами., Проверяет ошибку статуса без регистрации., Проверяет статус зарегистрированного агента., Проверяет отдельную команду heartbeat., TestAgentCommands

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (8): Тесты модуля валидации и загрузки launch spec (terminal/spec.py)., Позитивные тесты валидации spec., Корректный spec проходит валидацию без ошибок., layout=multi-window проходит валидацию., Все допустимые CLI-типы проходят валидацию., Все допустимые роли проходят валидацию., Ровно 8 агентов проходят валидацию (максимум)., TestValidateSpecPositive

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (7): Тесты отключения встроенной справки., Корневой --help не должен раскрывать список команд., Подкоманды не должны поддерживать --help., Запуск без аргументов не должен печатать каталог команд., Проверяет отказ перезаписи без --force., Проверяет пересоздание с --force., TestHelpSuppression

### Community 25 - "Community 25"
Cohesion: 0.2
Nodes (8): logs_command(), Команда swarm logs.  Показывает историю событий из task_log., Показывает журнал событий системы., Команда swarm start.  Устанавливает флаг старта для агентов., _configure_stdio_for_unicode(), create_console(), Переключает stdout/stderr на UTF-8, чтобы Rich не падал на Unicode в Windows-кон, Создаёт Rich Console после безопасной настройки кодировки потоков.

### Community 26 - "Community 26"
Cohesion: 0.18
Nodes (6): Проверяет пустой журнал., Проверяет журнал с событиями., Проверяет параметр --limit., Проверяет параметр --since., Создание задачи записывает task_created в лог., TestLogsCommand

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (7): Интеграционные тесты CLI., Проверяет создание БД., Проверяет создание скиллов для агентов и оркестратора., Тесты unlock с флагом --agent., unlock --file X --agent имя снимает блокировку без env vars., TestInitCommand, TestUnlockWithAgentFlag

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (7): Тесты распределения и выполнения задач., Тесты завершения задач., Проверяет ошибку при завершении без задачи., Проверяет что сброс pending задачи — noop., Проверяет сброс несуществующей задачи., TestTaskCompletion, TestTaskReset

### Community 29 - "Community 29"
Cohesion: 0.24
Nodes (7): _log_entry_row(), Тесты десериализации TaskLogEntry из строки БД., Валидный тип события парсится корректно., Неизвестный тип события не бросает ValueError., Сообщение лога сохраняется без изменений., Возвращает словарь, имитирующий строку из таблицы task_log., TestTaskLogEntryFromRow

### Community 30 - "Community 30"
Cohesion: 0.2
Nodes (8): _progress_bar(), Текстовый прогресс-бар: [████████░░░░] 42%., Запускает TUI-монитор., run_tui(), find_db_path(), Ищет файл swarm.db в текущей директории и родительских., check_db(), Проверяет наличие БД. Завершает процесс, если не найдена.

### Community 31 - "Community 31"
Cohesion: 0.2
Nodes (6): Тесты команд управления задачами., Проверяет создание задачи., Проверяет создание задачи с фильтрами., Проверяет пустой список задач., Проверяет список с задачами., TestTaskCommands

### Community 32 - "Community 32"
Cohesion: 0.2
Nodes (6): Тесты команд lock и unlock., Полный цикл блокировки и разблокировки., Блокировка без активной задачи даёт ошибку., unlock --all --force снимает все блокировки., Лидер/оркестратор может использовать --all --force без регистрации., TestLockUnlockCommands

### Community 33 - "Community 33"
Cohesion: 0.2
Nodes (6): Тесты получения и завершения задач., Проверяет поведение при отсутствии задач., Проверяет получение задачи., Проверяет завершение задачи., Проверяет ошибку завершения без задачи., TestNextAndDone

### Community 34 - "Community 34"
Cohesion: 0.27
Nodes (10): Terminal Orchestration, get_launcher_path, _agent_sort_key, _build_mixed_window_args, _chunks, _pane_command, _start_wt_process, launch_layout (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.25
Nodes (5): Валидный статус задачи парсится корректно., Неизвестный статус задачи не бросает ValueError., Необязательные поля корректно принимают None., Возвращает словарь, имитирующий строку из таблицы tasks., _task_row()

### Community 36 - "Community 36"
Cohesion: 0.25
Nodes (5): Тесты валидации имени агента (m-9)., Допустимые имена не вызывают исключения., Недопустимые имена вызывают ValueError., Регистрация дублирующего имени вызывает IntegrityError., TestValidateAgentName

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (5): Проверяет получение агента по токену., Проверяет поведение при неверном токене., Тесты операций с агентами., Проверяет регистрацию агента., TestAgents

### Community 38 - "Community 38"
Cohesion: 0.25
Nodes (5): _fmt_dt(), Обновляет полную таблицу агентов., Обновляет таблицу ВСЕХ задач (включая done/failed)., Форматирует детальную информацию о задаче., Форматирует datetime для отображения.

### Community 39 - "Community 39"
Cohesion: 0.25
Nodes (7): Общие фикстуры для тестов SWARM., Создаёт временную базу данных для тестов.      Очищает переменные окружения SWAR, Создаёт тестового агента., Создаёт тестовую задачу., sample_agent(), sample_task(), temp_db()

### Community 40 - "Community 40"
Cohesion: 0.25
Nodes (5): Тесты ограничений прав для агента., Агент не должен менять очередь задач., Лидер/оркестратор может использовать --force без регистрации., Зарегистрированный агент может использовать --force для разблокировки., TestPermissions

### Community 41 - "Community 41"
Cohesion: 0.25
Nodes (5): Тесты команды task reset., Сброс задачи через CLI., Сброс несуществующей задачи даёт ошибку., Агент не может сбрасывать задачи., TestTaskResetCommand

### Community 42 - "Community 42"
Cohesion: 0.25
Nodes (5): Тесты команды task close., Принудительное закрытие задачи через CLI., Закрытие несуществующей задачи даёт ошибку., Агент не может закрывать задачи., TestTaskCloseCommand

### Community 43 - "Community 43"
Cohesion: 0.25
Nodes (5): Тесты общего модуля commands/common.py.  Проверяет _check_agent: поиск агента по, Тесты функции _check_agent., _check_agent бросает typer.Exit при несуществующем агенте., _check_agent бросает typer.Exit если нет сессии и имя не указано., TestCheckAgent

### Community 44 - "Community 44"
Cohesion: 0.25
Nodes (5): Тесты для команд блокировки файлов (lock.py).  Включает тест КРИТ-2: при таймаут, Тесты таймаута блокировки (КРИТ-2)., КРИТ-2: При таймауте ожидания блокировки статус агента     должен быть восстанов, Если таймаут наступил до того как агент вошёл в состояние WAITING     (timeout=0, TestLockTimeout

### Community 45 - "Community 45"
Cohesion: 0.33
Nodes (7): Launch Spec, _validate_spec, LaunchAgentSpec, LaunchSpec, LayoutSpec, load_launch_spec, save_launch_spec

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (4): Тесты КРИТ-4: create_task с BEGIN IMMEDIATE транзакцией., Создание задачи с зависимостью корректно работает в транзакции., Создание задачи без зависимости работает в транзакции., TestCreateTaskTransaction

### Community 47 - "Community 47"
Cohesion: 0.33
Nodes (4): Тесты операций с задачами., Проверяет создание задачи., Проверяет получение задачи по ID., TestTasks

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (4): _launch_session_row(), Валидный статус launch-сессии парсится корректно., Неизвестный статус launch-сессии не бросает ValueError., Возвращает словарь, имитирующий строку из таблицы launch_sessions.

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (4): Тесты команды task assign., Назначение задачи через CLI., Назначение несуществующей задачи даёт ошибку., TestTaskAssignCommand

### Community 50 - "Community 50"
Cohesion: 0.4
Nodes (5): _find_cli_binary(), Preflight-проверки перед запуском терминальных агентов., Пытается найти исполняемый файл CLI-агента., Выполняет preflight-проверки и возвращает список ошибок., run_preflight()

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (4): get_agent_by_name(), Получает агента по имени., Принудительное закрытие освобождает назначенного агента., Находит существующего агента.

### Community 52 - "Community 52"
Cohesion: 0.4
Nodes (3): _fmt_duration_mins(), Обновляет полную таблицу блокировок., Форматирует длительность в минутах.

### Community 53 - "Community 53"
Cohesion: 0.4
Nodes (3): Проверяет start без агентов., Проверяет start --all., TestStartCommand

### Community 54 - "Community 54"
Cohesion: 0.5
Nodes (3): App, main(), Главный модуль CLI для SWARM.  Точка входа для всех команд: - swarm init — ин

## Knowledge Gaps
- **514 isolated node(s):** `Главный модуль CLI для SWARM.  Точка входа для всех команд: - swarm init — ин`, `Модуль работы с базой данных SWARM.  Реализует: - Подключение к SQLite с WAL-`, `Ищет файл swarm.db в текущей директории и родительских.`, `Возвращает путь к файлу БД или бросает FileNotFoundError.`, `Контекстный менеджер для подключения к БД.` (+509 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestTerminalCommands` connect `TUI Formatting & Status` to `Community 27`?**
  _High betweenness centrality (0.182) - this node is a cross-community bridge._
- **Why does `TaskStatus` connect `Models & Enums` to `Task Assignment & Locks`, `TUI Formatting & Status`, `Community 37`, `Community 36`, `Database File Locking`, `TUI Overview Panels`, `Edge Cases Tests`, `Monitor Dashboard`, `Community 46`, `Community 47`, `Models Tests`, `Community 17`, `Community 18`, `Community 28`, `Community 29`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Why does `_validate_spec()` connect `Terminal Spec Validation` to `Community 23`, `Terminal Launch Commands`, `Community 15`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `register_agent()` (e.g. with `join_command()` and `sample_agent()`) actually correct?**
  _`register_agent()` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `create_task()` (e.g. with `add_command()` and `sample_task()`) actually correct?**
  _`create_task()` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `str` (e.g. with `get_connection()` and `init_database()`) actually correct?**
  _`str` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `TaskStatus` (e.g. with `StatsBar` and `OverviewAgentsPanel`) actually correct?**
  _`TaskStatus` has 42 INFERRED edges - model-reasoned connections that need verification._
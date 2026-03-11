"""
Тесты модуля базы данных.
"""

import sqlite3
import threading
from pathlib import Path

import pytest

from swarm.db import (
    DB_FILENAME,
    SESSIONS_DIR,
    add_launch_session_agent,
    assign_task_to_agent,
    claim_next_task,
    cleanup_dead_agents,
    complete_task,
    create_launch_session,
    create_task,
    find_db_path,
    force_close_task,
    get_active_launch_agent_names,
    get_agent_by_name,
    get_agent_by_session,
    get_all_agents,
    get_all_locks,
    get_all_tasks,
    get_file_lock,
    get_launch_session,
    get_launch_session_agents,
    get_launch_sessions,
    get_recent_events,
    get_task,
    init_database,
    load_session_token,
    log_event,
    reconcile_launch_session,
    register_agent,
    save_session_token,
    try_lock_file,
    unlock_file,
    unlock_task_files,
    update_launch_agent_status,
    update_launch_session_status,
    validate_agent_name,
)
from swarm.models import AgentStatus, EventType, LaunchRegistrationStatus, LaunchSessionStatus, TaskStatus


class TestDatabaseInit:
    """Тесты инициализации БД."""

    def test_init_creates_db_file(self, tmp_path):
        """Проверяет создание файла БД."""
        db_path = init_database(tmp_path)

        assert db_path.exists()
        assert db_path.name == DB_FILENAME

    def test_init_creates_wal_mode(self, tmp_path):
        """Проверяет включение WAL-режима."""
        import sqlite3

        db_path = init_database(tmp_path)

        conn = sqlite3.connect(str(db_path))
        result = conn.execute("PRAGMA journal_mode").fetchone()
        conn.close()

        assert result[0] == "wal"

    def test_find_db_path(self, temp_db):
        """Проверяет поиск БД."""
        found = find_db_path()

        assert found is not None
        assert found.exists()


class TestAgents:
    """Тесты операций с агентами."""

    def test_register_agent(self, temp_db):
        """Проверяет регистрацию агента."""
        agent = register_agent(
            session_token="unique-token-001",
            cli_type="claude",
            name="alice",
            role="architect",
        )

        assert agent.agent_id is not None
        assert agent.session_token == "unique-token-001"
        assert agent.cli_type == "claude"
        assert agent.name == "alice"
        assert agent.role == "architect"
        assert agent.status == AgentStatus.IDLE

    def test_get_agent_by_session(self, sample_agent):
        """Проверяет получение агента по токену."""
        found = get_agent_by_session("test-token-123")

        assert found is not None
        assert found.agent_id == sample_agent.agent_id
        assert found.name == sample_agent.name

    def test_get_agent_by_invalid_session(self, temp_db):
        """Проверяет поведение при неверном токене."""
        found = get_agent_by_session("nonexistent-token")

        assert found is None

    def test_get_all_agents(self, temp_db):
        """Проверяет получение списка агентов."""
        register_agent("token-1", "claude", "agent1", "developer")
        register_agent("token-2", "codex", "agent2", "tester")

        agents = get_all_agents()

        assert len(agents) == 2
        assert agents[0].name == "agent1"
        assert agents[1].name == "agent2"


class TestTasks:
    """Тесты операций с задачами."""

    def test_create_task(self, temp_db):
        """Проверяет создание задачи."""
        task = create_task(
            description="Реализовать API",
            priority=1,
            target_role="developer",
        )

        assert task.task_id is not None
        assert task.description == "Реализовать API"
        assert task.priority == 1
        assert task.target_role == "developer"
        assert task.status == TaskStatus.PENDING

    def test_get_task(self, sample_task):
        """Проверяет получение задачи по ID."""
        found = get_task(sample_task.task_id)

        assert found is not None
        assert found.task_id == sample_task.task_id
        assert found.description == sample_task.description

    def test_get_all_tasks(self, temp_db):
        """Проверяет получение списка задач."""
        create_task("Задача 1", priority=3)
        create_task("Задача 2", priority=1)
        create_task("Задача 3", priority=2)

        tasks = get_all_tasks()

        assert len(tasks) == 3
        # Проверяем сортировку по приоритету
        assert tasks[0].priority == 1
        assert tasks[1].priority == 2
        assert tasks[2].priority == 3

    def test_get_tasks_by_status(self, temp_db):
        """Проверяет фильтрацию по статусу."""
        create_task("Задача pending")

        pending = get_all_tasks(status=TaskStatus.PENDING)
        done = get_all_tasks(status=TaskStatus.DONE)

        assert len(pending) == 1
        assert len(done) == 0


class TestFileLocks:
    """Тесты блокировки файлов."""

    def test_lock_file(self, sample_agent, sample_task):
        """Проверяет захват блокировки."""
        success = try_lock_file(
            agent_id=sample_agent.agent_id,
            task_id=sample_task.task_id,
            file_path="src/main.py",
        )

        assert success is True

        lock = get_file_lock("src/main.py")
        assert lock is not None
        assert lock.locked_by == sample_agent.agent_id

    def test_lock_already_locked_file(self, temp_db):
        """Проверяет блокировку уже заблокированного файла."""
        agent1 = register_agent("token-1", "claude", "agent1", "developer")
        agent2 = register_agent("token-2", "claude", "agent2", "developer")

        task1 = create_task("Задача 1")
        task2 = create_task("Задача 2")

        # Первый агент блокирует
        success1 = try_lock_file(agent1.agent_id, task1.task_id, "file.py")
        assert success1 is True

        # Второй агент пытается заблокировать тот же файл
        success2 = try_lock_file(agent2.agent_id, task2.task_id, "file.py")
        assert success2 is False

    def test_unlock_file(self, sample_agent, sample_task):
        """Проверяет снятие блокировки."""
        try_lock_file(sample_agent.agent_id, sample_task.task_id, "test.py")

        result = unlock_file("test.py", agent_id=sample_agent.agent_id)

        assert result is True
        assert get_file_lock("test.py") is None

    def test_force_unlock(self, temp_db):
        """Проверяет принудительное снятие блокировки."""
        agent = register_agent("token", "claude", "agent", "developer")
        task = create_task("Задача")

        try_lock_file(agent.agent_id, task.task_id, "locked.py")

        # Принудительное снятие без указания агента
        result = unlock_file("locked.py", force=True)

        assert result is True
        assert get_file_lock("locked.py") is None

    def test_agent_cannot_lock_two_files_at_once(self, sample_agent, sample_task):
        """Проверяет ограничение на одну активную блокировку у агента."""
        first = try_lock_file(sample_agent.agent_id, sample_task.task_id, "first.py")
        second = try_lock_file(sample_agent.agent_id, sample_task.task_id, "second.py")

        assert first is True
        assert second is False
        assert get_file_lock("second.py") is None


class TestCleanup:
    """Тесты очистки неактивных агентов."""

    def test_cleanup_keeps_agent_with_stale_heartbeat_and_live_pid(self, temp_db, monkeypatch):
        """Живой процесс не должен удаляться только из-за старого heartbeat."""
        register_agent("token-live", "claude", "live-agent", "developer", pid=9999)

        db_path = Path.cwd() / DB_FILENAME
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "UPDATE agents SET last_heartbeat = datetime('now', '-31 minutes') WHERE name = ?",
                ("live-agent",),
            )
            conn.commit()

        monkeypatch.setattr("swarm.db.is_process_alive", lambda pid: True)

        removed = cleanup_dead_agents(timeout_minutes=30, check_pid=True)

        assert removed == 0
        assert get_all_agents()[0].name == "live-agent"

    def test_cleanup_removes_agent_with_stale_heartbeat_and_dead_pid(self, temp_db, monkeypatch):
        """Мёртвый процесс должен удаляться даже если агент ещё есть в таблице."""
        register_agent("token-dead", "claude", "dead-agent", "developer", pid=9998)

        db_path = Path.cwd() / DB_FILENAME
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "UPDATE agents SET last_heartbeat = datetime('now', '-31 minutes') WHERE name = ?",
                ("dead-agent",),
            )
            conn.commit()

        monkeypatch.setattr("swarm.db.is_process_alive", lambda pid: False)

        removed = cleanup_dead_agents(timeout_minutes=30, check_pid=True)

        assert removed == 1
        assert get_all_agents() == []


class TestAssignTask:
    """Тесты назначения задач агентам."""

    def test_assign_task_to_agent(self, temp_db):
        """Успешное назначение задачи агенту."""
        agent = register_agent("tok-a1", "claude", "worker", "developer")
        task = create_task("Реализовать фичу", priority=2)

        result = assign_task_to_agent(task.task_id, agent.name)

        assert result is True
        # Проверяем, что target_name обновился
        updated = get_task(task.task_id)
        assert updated.target_name == agent.name

    def test_assign_already_in_progress(self, temp_db):
        """Нельзя назначить задачу, которая уже выполняется."""
        agent = register_agent("tok-a2", "claude", "busy", "developer")
        create_task("Задача в работе", priority=1)

        # Агент захватывает задачу — она переходит в in_progress
        claimed = claim_next_task(agent)
        assert claimed is not None

        # Попытка назначить задачу в статусе in_progress
        result = assign_task_to_agent(claimed.task_id, "other-agent")
        assert result is False

    def test_assign_nonexistent_task(self, temp_db):
        """Возвращает False для несуществующей задачи."""
        result = assign_task_to_agent(99999, "any-agent")
        assert result is False


class TestForceCloseTask:
    """Тесты принудительного закрытия задач."""

    def test_force_close_task(self, temp_db):
        """Принудительное закрытие задачи переводит её в done."""
        task = create_task("Задача для закрытия", priority=2)

        result = force_close_task(task.task_id, reason="Тестовое закрытие")

        assert result is True
        closed = get_task(task.task_id)
        assert closed.status == TaskStatus.DONE
        assert closed.summary == "Тестовое закрытие"

    def test_force_close_releases_locks(self, temp_db):
        """Принудительное закрытие снимает блокировки файлов задачи."""
        agent = register_agent("tok-fc1", "claude", "locker", "developer")
        create_task("Задача с блокировкой")

        # Захватываем задачу и блокируем файл
        claimed = claim_next_task(agent)
        try_lock_file(agent.agent_id, claimed.task_id, "src/module.py")

        # Проверяем наличие блокировки
        assert get_file_lock("src/module.py") is not None

        # Принудительно закрываем
        force_close_task(claimed.task_id, reason="Закрытие с блокировками")

        # Блокировка должна быть снята
        assert get_file_lock("src/module.py") is None

    def test_force_close_frees_agent(self, temp_db):
        """Принудительное закрытие освобождает назначенного агента."""
        agent = register_agent("tok-fc2", "claude", "worker-fc", "developer")
        task = create_task("Задача для освобождения агента")

        # Агент захватывает задачу
        claim_next_task(agent)

        # Проверяем что агент работает
        busy = get_agent_by_name("worker-fc")
        assert busy.status == AgentStatus.WORKING
        assert busy.current_task_id == task.task_id

        # Принудительно закрываем задачу
        force_close_task(task.task_id)

        # Агент должен стать idle и не иметь текущей задачи
        freed = get_agent_by_name("worker-fc")
        assert freed.status == AgentStatus.IDLE
        assert freed.current_task_id is None

    def test_force_close_nonexistent(self, temp_db):
        """Возвращает False для несуществующей задачи."""
        result = force_close_task(99999)
        assert result is False

    def test_force_close_already_done(self, temp_db):
        """Для уже завершённой задачи возвращает True без изменений."""
        agent = register_agent("tok-fc3", "claude", "finisher", "developer")
        task = create_task("Задача для двойного закрытия")

        # Захватываем и завершаем задачу штатно
        claim_next_task(agent)
        complete_task(agent, summary="Всё готово")

        # Проверяем что задача завершена
        done_task = get_task(task.task_id)
        assert done_task.status == TaskStatus.DONE

        # Повторное принудительное закрытие должно вернуть True
        result = force_close_task(task.task_id, reason="Повторное закрытие")
        assert result is True


class TestCleanupDeadAgentsTasks:
    """Тесты очистки задач и блокировок мёртвых агентов."""

    def test_cleanup_releases_tasks_and_locks(self, temp_db, monkeypatch):
        """При удалении мёртвого агента его задачи переходят в failed, блокировки снимаются."""
        # Регистрируем агента с PID
        agent = register_agent("tok-dead", "claude", "dead-worker", "developer", pid=7777)
        task = create_task("Задача мёртвого агента")

        # Агент захватывает задачу и блокирует файл
        claimed = claim_next_task(agent)
        try_lock_file(agent.agent_id, claimed.task_id, "src/dead_file.py")

        # Проверяем начальное состояние
        assert get_task(task.task_id).status == TaskStatus.IN_PROGRESS
        assert get_file_lock("src/dead_file.py") is not None

        # Устариваем heartbeat агента
        db_path = Path.cwd() / DB_FILENAME
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "UPDATE agents SET last_heartbeat = datetime('now', '-31 minutes') WHERE name = ?",
                ("dead-worker",),
            )
            conn.commit()

        # Процесс мёртв
        monkeypatch.setattr("swarm.db.is_process_alive", lambda pid: False)

        # Запускаем очистку
        removed = cleanup_dead_agents(timeout_minutes=30, check_pid=True)

        assert removed == 1

        # Задача должна перейти в failed
        failed_task = get_task(task.task_id)
        assert failed_task.status == TaskStatus.FAILED
        assert failed_task.assigned_to is None

        # Блокировка должна быть снята
        assert get_file_lock("src/dead_file.py") is None

        # Агент должен быть удалён
        assert get_agent_by_name("dead-worker") is None


class TestGetAgentByName:
    """Тесты получения агента по имени."""

    def test_get_existing_agent(self, temp_db):
        """Находит существующего агента."""
        register_agent("tok-name1", "claude", "finder", "developer")
        found = get_agent_by_name("finder")
        assert found is not None
        assert found.name == "finder"

    def test_get_nonexistent_agent(self, temp_db):
        """Возвращает None для несуществующего имени."""
        assert get_agent_by_name("ghost") is None


class TestGetAllLocks:
    """Тесты получения всех блокировок."""

    def test_empty_locks(self, temp_db):
        """Пустой список при отсутствии блокировок."""
        assert get_all_locks() == []

    def test_returns_all_locks(self, temp_db):
        """Возвращает все активные блокировки."""
        a1 = register_agent("tok-l1", "claude", "locker1", "developer")
        a2 = register_agent("tok-l2", "codex", "locker2", "developer")
        t1 = create_task("Задача 1")
        t2 = create_task("Задача 2")

        try_lock_file(a1.agent_id, t1.task_id, "file_a.py")
        try_lock_file(a2.agent_id, t2.task_id, "file_b.py")

        locks = get_all_locks()
        assert len(locks) == 2
        paths = {lock.file_path for lock in locks}
        assert "file_a.py" in paths
        assert "file_b.py" in paths


class TestUnlockTaskFiles:
    """Тесты снятия всех блокировок задачи."""

    def test_unlock_removes_task_locks(self, temp_db):
        """Снимает все блокировки, привязанные к задаче."""
        agent = register_agent("tok-ut1", "claude", "unlocker", "developer")
        task = create_task("Задача")

        try_lock_file(agent.agent_id, task.task_id, "one.py")

        removed = unlock_task_files(task.task_id)
        assert removed == 1
        assert get_file_lock("one.py") is None

    def test_unlock_nonexistent_task(self, temp_db):
        """Для задачи без блокировок возвращает 0."""
        assert unlock_task_files(99999) == 0


class TestValidateAgentName:
    """Тесты валидации имени агента (m-9)."""

    def test_valid_names(self):
        """Допустимые имена не вызывают исключения."""
        for name in ["agent-1", "claude_worker", "A", "test123", "a" * 32]:
            validate_agent_name(name)

    def test_invalid_names(self):
        """Недопустимые имена вызывают ValueError."""
        for name in ["", "a" * 33, "hello world", "agent/bad", "агент", "../etc"]:
            with pytest.raises(ValueError):
                validate_agent_name(name)

    def test_duplicate_name_rejected(self, temp_db):
        """Регистрация дублирующего имени вызывает IntegrityError."""
        register_agent("tok-dup1", "claude", "unique-name", "developer")
        with pytest.raises(sqlite3.IntegrityError):
            register_agent("tok-dup2", "codex", "unique-name", "tester")


class TestDependencyCycle:
    """Тесты обнаружения циклов в зависимостях (m-10)."""

    def test_no_cycle(self, temp_db):
        """Линейная цепочка зависимостей не вызывает ошибок."""
        t1 = create_task("Первая")
        t2 = create_task("Вторая", depends_on=t1.task_id)
        t3 = create_task("Третья", depends_on=t2.task_id)
        assert t3.depends_on == t2.task_id

    def test_linear_dependency_is_valid(self, temp_db):
        """Линейная зависимость t2 -> t1 допустима (не цикл)."""
        t1 = create_task("Задача")
        t2 = create_task("Зависимая", depends_on=t1.task_id)
        assert t2 is not None
        assert t2.depends_on == t1.task_id

    def test_self_dependency_detected(self, temp_db):
        """Задача не может зависеть от самой себя (цикл длины 1).

        Прямая самозависимость: создаём задачу, затем пытаемся
        вручную установить depends_on на собственный task_id через SQL,
        и проверяем через _has_dependency_cycle.
        """
        import sqlite3 as _sqlite3

        from swarm.db import _has_dependency_cycle, get_db_path

        t1 = create_task("Задача-одиночка")

        # Устанавливаем depends_on = task_id задачи на саму себя
        db_path = get_db_path()
        conn = _sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE tasks SET depends_on = ? WHERE task_id = ?",
            (t1.task_id, t1.task_id),
        )
        conn.commit()

        # Функция обнаружения цикла должна обнаружить самозависимость
        conn.row_factory = _sqlite3.Row
        assert _has_dependency_cycle(conn, t1.task_id) is True
        conn.close()


class TestConcurrency:
    """Тесты конкурентного доступа (M-10)."""

    def test_concurrent_claim_single_task(self, temp_db):
        """Только один агент должен захватить задачу при конкурентном доступе."""
        agents = []
        for i in range(5):
            a = register_agent(f"tok-cc{i}", "claude", f"racer-{i}", "developer")
            agents.append(a)

        create_task("Единственная задача", priority=1)

        results = [None] * len(agents)
        errors = []

        def worker(idx, agent):
            try:
                results[idx] = claim_next_task(agent)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i, a)) for i, a in enumerate(agents)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Ошибки в потоках: {errors}"
        claimed = [r for r in results if r is not None]
        assert len(claimed) == 1, f"Ожидался 1 захват, получено {len(claimed)}"

    def test_concurrent_lock_same_file(self, temp_db):
        """Только один агент должен заблокировать файл при конкурентном доступе."""
        agents = []
        tasks = []
        for i in range(5):
            a = register_agent(f"tok-cl{i}", "claude", f"locker-{i}", "developer")
            t = create_task(f"Задача {i}")
            agents.append(a)
            tasks.append(t)

        results = [None] * len(agents)

        def worker(idx):
            results[idx] = try_lock_file(agents[idx].agent_id, tasks[idx].task_id, "contested.py")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(agents))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        wins = [r for r in results if r is True]
        assert len(wins) == 1, f"Ожидался 1 захват блокировки, получено {len(wins)}"

    def test_concurrent_complete_task(self, temp_db):
        """complete_task при конкурентном вызове не создаёт дублей."""
        agent = register_agent("tok-cct", "claude", "completer", "developer")
        create_task("Задача для завершения")
        claim_next_task(agent)

        results = [None] * 3

        def worker(idx):
            results[idx] = complete_task(agent, f"Резюме от потока {idx}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [r for r in results if r is True]
        assert len(successes) == 1, f"Ожидалось 1 успешное завершение, получено {len(successes)}"


class TestEventLogging:
    """Тесты логирования событий."""

    def test_register_agent_logs_event(self, temp_db):
        """Регистрация агента создаёт запись в логе."""
        agent = register_agent("tok-log1", "claude", "logger-1", "developer")
        events = get_recent_events(limit=10)
        registered = [e for e in events if e.event == EventType.AGENT_REGISTERED]
        assert len(registered) == 1
        assert registered[0].agent_id == agent.agent_id
        assert "logger-1" in registered[0].message

    def test_claim_task_logs_event(self, temp_db):
        """Захват задачи создаёт запись task_started."""
        agent = register_agent("tok-log2", "claude", "logger-2", "developer")
        task = create_task("Задача для лога")
        claim_next_task(agent)
        events = get_recent_events(limit=10)
        started = [e for e in events if e.event == EventType.TASK_STARTED]
        assert len(started) == 1
        assert started[0].task_id == task.task_id

    def test_complete_task_logs_event(self, temp_db):
        """Завершение задачи создаёт запись task_done с резюме."""
        agent = register_agent("tok-log3", "claude", "logger-3", "developer")
        create_task("Задача для завершения")
        claim_next_task(agent)
        complete_task(agent, "Готово: всё сделано")
        events = get_recent_events(limit=10)
        done = [e for e in events if e.event == EventType.TASK_DONE]
        assert len(done) == 1
        assert "Готово: всё сделано" in done[0].message

    def test_lock_file_logs_event(self, temp_db):
        """Блокировка файла создаёт запись file_locked."""
        agent = register_agent("tok-log4", "claude", "logger-4", "developer")
        task = create_task("Задача с блокировкой")
        claim_next_task(agent)
        try_lock_file(agent.agent_id, task.task_id, "test_file.py")
        events = get_recent_events(limit=10)
        locked = [e for e in events if e.event == EventType.FILE_LOCKED]
        assert len(locked) == 1
        assert "test_file.py" in locked[0].message

    def test_log_event_standalone(self, temp_db):
        """Функция log_event записывает произвольное событие."""
        log_event(EventType.ERROR, task_id=None, agent_id=None, message="Тестовая ошибка")
        events = get_recent_events(limit=5)
        errors = [e for e in events if e.event == EventType.ERROR]
        assert len(errors) == 1
        assert errors[0].message == "Тестовая ошибка"

    def test_get_recent_events_limit(self, temp_db):
        """Параметр limit ограничивает количество возвращаемых событий."""
        for i in range(10):
            log_event(EventType.ERROR, message=f"Событие {i}")
        events = get_recent_events(limit=3)
        assert len(events) == 3

    def test_get_recent_events_filter_by_task(self, temp_db):
        """Фильтрация событий по task_id."""
        log_event(EventType.ERROR, task_id=100, message="Для задачи 100")
        log_event(EventType.ERROR, task_id=200, message="Для задачи 200")
        events = get_recent_events(limit=10, task_id=100)
        assert len(events) == 1
        assert events[0].task_id == 100

    def test_get_recent_events_filter_by_agent(self, temp_db):
        """Фильтрация событий по agent_id."""
        agent = register_agent("tok-log5", "claude", "logger-5", "developer")
        log_event(EventType.ERROR, agent_id=agent.agent_id, message="От агента")
        log_event(EventType.ERROR, agent_id=999, message="От другого")
        events = get_recent_events(limit=10, agent_id=agent.agent_id)
        # +1 за agent_registered
        agent_events = [e for e in events if e.event == EventType.ERROR]
        assert len(agent_events) == 1

    def test_get_recent_events_since_hours(self, temp_db):
        """Фильтрация по since_hours возвращает только свежие события."""
        log_event(EventType.ERROR, message="Свежее событие")
        # since_hours=24 должен вернуть событие, созданное только что
        events = get_recent_events(limit=100, since_hours=24)
        assert len(events) >= 1
        # since_hours=0 (ноль часов назад) — может не вернуть ничего или только мгновенные
        # Проверяем что фильтр не ломается
        events_zero = get_recent_events(limit=100, since_hours=0.0001)
        assert isinstance(events_zero, list)

    def test_cleanup_dead_agents_logs_event(self, temp_db):
        """Очистка мёртвых агентов записывает agent_cleanup в лог."""
        agent = register_agent("tok-log6", "claude", "logger-6", "developer", pid=999999)
        cleanup_dead_agents(timeout_minutes=0, check_pid=True)
        events = get_recent_events(limit=10)
        cleanup = [e for e in events if e.event == EventType.AGENT_CLEANUP]
        assert len(cleanup) == 1
        assert str(agent.agent_id) in cleanup[0].message

    def test_new_event_types_exist(self, temp_db):
        """Все новые типы событий доступны в EventType."""
        assert EventType.TASK_CREATED.value == "task_created"
        assert EventType.TASK_ASSIGNED.value == "task_assigned"
        assert EventType.TASK_FORCE_CLOSED.value == "task_force_closed"
        assert EventType.AGENT_CLEANUP.value == "agent_cleanup"


class TestLaunchSessions:
    """Тесты launch sessions для терминальной оркестрации."""

    def test_create_and_get_launch_session(self, temp_db):
        """Создание launch session и чтение из БД."""
        created = create_launch_session(
            session_id="ls-test-1",
            working_directory=str(Path.cwd()),
            approval_mode="yolo",
            layout_mode="mixed",
            requested_agent_count=2,
            created_by="orchestrator",
            status=LaunchSessionStatus.PLANNED,
        )

        assert created.session_id == "ls-test-1"
        assert created.status == LaunchSessionStatus.PLANNED

        found = get_launch_session("ls-test-1")
        assert found is not None
        assert found.layout_mode == "mixed"

    def test_add_launch_session_agent_and_status_update(self, temp_db):
        """Добавление агента в launch session и обновление статуса."""
        create_launch_session(
            session_id="ls-test-2",
            working_directory=str(Path.cwd()),
            approval_mode="safe",
            layout_mode="single",
            requested_agent_count=1,
        )
        add_launch_session_agent(
            session_id="ls-test-2",
            cli_type="claude",
            agent_name="launch-dev",
            agent_role="developer",
            window_index=1,
            pane_index=1,
            launcher_profile="claude-safe",
            bootstrap_prompt="test prompt",
            registration_status=LaunchRegistrationStatus.PLANNED,
        )

        updated = update_launch_agent_status(
            "ls-test-2",
            "launch-dev",
            LaunchRegistrationStatus.LAUNCHED,
            terminal_pid=4321,
        )
        assert updated is True

        agents = get_launch_session_agents("ls-test-2")
        assert len(agents) == 1
        assert agents[0].registration_status == LaunchRegistrationStatus.LAUNCHED
        assert agents[0].terminal_pid == 4321

    def test_reconcile_marks_registered_agents(self, temp_db):
        """reconcile связывает launch-агентов с фактически зарегистрированными."""
        create_launch_session(
            session_id="ls-test-3",
            working_directory=str(Path.cwd()),
            approval_mode="safe",
            layout_mode="single",
            requested_agent_count=1,
            status=LaunchSessionStatus.LAUNCHED,
        )
        add_launch_session_agent(
            session_id="ls-test-3",
            cli_type="claude",
            agent_name="registered-agent",
            agent_role="developer",
            window_index=1,
            pane_index=1,
            launcher_profile="claude-safe",
            bootstrap_prompt="prompt",
            registration_status=LaunchRegistrationStatus.LAUNCHED,
        )

        registered = register_agent("tok-ls-3", "claude", "registered-agent", "developer")
        session, launch_agents = reconcile_launch_session("ls-test-3")

        assert session is not None
        assert session.status == LaunchSessionStatus.REGISTERED
        assert len(launch_agents) == 1
        assert launch_agents[0].registration_status == LaunchRegistrationStatus.REGISTERED
        assert launch_agents[0].registered_agent_id == registered.agent_id

    def test_active_launch_agent_names(self, temp_db):
        """В активные имена попадают только незавершённые launch sessions."""
        create_launch_session(
            session_id="ls-active",
            working_directory=str(Path.cwd()),
            approval_mode="safe",
            layout_mode="single",
            requested_agent_count=1,
            status=LaunchSessionStatus.APPROVED,
        )
        add_launch_session_agent(
            session_id="ls-active",
            cli_type="codex",
            agent_name="busy-name",
            agent_role="developer",
            window_index=1,
            pane_index=1,
            launcher_profile="codex-safe",
            bootstrap_prompt="prompt",
        )

        create_launch_session(
            session_id="ls-stopped",
            working_directory=str(Path.cwd()),
            approval_mode="safe",
            layout_mode="single",
            requested_agent_count=1,
            status=LaunchSessionStatus.STOPPED,
        )
        add_launch_session_agent(
            session_id="ls-stopped",
            cli_type="codex",
            agent_name="free-name",
            agent_role="developer",
            window_index=1,
            pane_index=1,
            launcher_profile="codex-safe",
            bootstrap_prompt="prompt",
        )

        names = get_active_launch_agent_names()
        assert "busy-name" in names
        assert "free-name" not in names

    def test_update_launch_session_status_and_list(self, temp_db):
        """Обновление статуса сессии отражается в выборке."""
        create_launch_session(
            session_id="ls-test-4",
            working_directory=str(Path.cwd()),
            approval_mode="yolo",
            layout_mode="mixed",
            requested_agent_count=3,
            status=LaunchSessionStatus.PLANNED,
        )

        changed = update_launch_session_status("ls-test-4", LaunchSessionStatus.APPROVED)
        assert changed is True

        sessions = get_launch_sessions(status=LaunchSessionStatus.APPROVED)
        assert len(sessions) == 1
        assert sessions[0].session_id == "ls-test-4"


class TestCleanupForceAll:
    """Тесты КРИТ-1: cleanup_dead_agents(force_all=True) освобождает задачи и блокировки."""

    def test_force_all_releases_tasks(self, temp_db):
        """При force_all=True задачи in_progress переходят в failed."""
        agent = register_agent("tok-fa1", "claude", "force-agent", "developer")
        task = create_task("Задача для force_all")

        # Агент захватывает задачу
        claim_next_task(agent)
        assert get_task(task.task_id).status == TaskStatus.IN_PROGRESS

        # Удаляем всех агентов принудительно
        removed = cleanup_dead_agents(force_all=True)
        assert removed == 1

        # Задача должна стать failed с assigned_to = NULL
        updated_task = get_task(task.task_id)
        assert updated_task.status == TaskStatus.FAILED
        assert updated_task.assigned_to is None

    def test_force_all_deletes_locks(self, temp_db):
        """При force_all=True все блокировки файлов удаляются."""
        agent = register_agent("tok-fa2", "claude", "lock-agent", "developer")
        task = create_task("Задача с блокировкой")

        # Агент захватывает задачу и блокирует файл
        claim_next_task(agent)
        try_lock_file(agent.agent_id, task.task_id, "src/locked.py")
        assert get_file_lock("src/locked.py") is not None

        # Удаляем всех принудительно
        cleanup_dead_agents(force_all=True)

        # Блокировка должна быть снята
        assert get_file_lock("src/locked.py") is None
        assert get_all_locks() == []

    def test_force_all_removes_all_agents(self, temp_db):
        """При force_all=True все агенты удаляются."""
        register_agent("tok-fa3", "claude", "agent-a", "developer")
        register_agent("tok-fa4", "codex", "agent-b", "tester")

        removed = cleanup_dead_agents(force_all=True)
        assert removed == 2
        assert get_all_agents() == []

    def test_force_all_leaves_pending_tasks_unchanged(self, temp_db):
        """При force_all=True задачи в pending не затрагиваются."""
        register_agent("tok-fa5", "claude", "pending-agent", "developer")
        task = create_task("Задача в ожидании")

        cleanup_dead_agents(force_all=True)

        # Задача pending не должна стать failed
        updated = get_task(task.task_id)
        assert updated.status == TaskStatus.PENDING


class TestCreateTaskTransaction:
    """Тесты КРИТ-4: create_task с BEGIN IMMEDIATE транзакцией."""

    def test_create_task_with_dependency(self, temp_db):
        """Создание задачи с зависимостью корректно работает в транзакции."""
        t1 = create_task("Первая задача")
        t2 = create_task("Вторая задача", depends_on=t1.task_id)

        assert t2.depends_on == t1.task_id
        assert t2.status == TaskStatus.PENDING

    def test_create_task_with_long_chain(self, temp_db):
        """Цепочка зависимостей из нескольких задач создаётся корректно."""
        t1 = create_task("Шаг 1")
        t2 = create_task("Шаг 2", depends_on=t1.task_id)
        t3 = create_task("Шаг 3", depends_on=t2.task_id)

        assert t3.depends_on == t2.task_id
        assert get_task(t3.task_id) is not None

    def test_create_task_without_dependency(self, temp_db):
        """Создание задачи без зависимости работает в транзакции."""
        task = create_task("Простая задача", priority=1)

        assert task.task_id is not None
        assert task.depends_on is None


class TestForceCloseLogging:
    """Тесты КРИТ-5: force_close_task логирует ровно одно событие."""

    def test_force_close_logs_single_event(self, temp_db):
        """force_close_task создаёт ровно одну запись TASK_FORCE_CLOSED в логе."""
        task = create_task("Задача для лога")

        force_close_task(task.task_id, reason="Тест логирования")

        events = get_recent_events(limit=50)
        force_closed_events = [e for e in events if e.event == EventType.TASK_FORCE_CLOSED]
        # Должно быть ровно одно событие TASK_FORCE_CLOSED
        assert len(force_closed_events) == 1
        assert force_closed_events[0].task_id == task.task_id
        assert "Тест логирования" in force_closed_events[0].message

    def test_force_close_does_not_log_task_done(self, temp_db):
        """force_close_task НЕ создаёт запись TASK_DONE — только TASK_FORCE_CLOSED."""
        task = create_task("Задача для проверки типа события")

        force_close_task(task.task_id, reason="Причина")

        events = get_recent_events(limit=50)
        done_events = [e for e in events if e.event == EventType.TASK_DONE]
        # Событий TASK_DONE быть не должно
        assert len(done_events) == 0

    def test_reset_task_logs_single_event(self, temp_db):
        """reset_task создаёт ровно одну запись TASK_RESET в логе."""
        from swarm.db import reset_task

        agent = register_agent("tok-rl1", "claude", "reset-logger", "developer")
        task = create_task("Задача для сброса")

        # Захватываем задачу
        claim_next_task(agent)

        # Сбрасываем
        reset_task(task.task_id)

        events = get_recent_events(limit=50)
        reset_events = [e for e in events if e.event == EventType.TASK_RESET]
        assert len(reset_events) == 1
        assert reset_events[0].task_id == task.task_id


class TestSessionTokenEncoding:
    """Тесты ВАЖ-4: save_session_token и load_session_token с utf-8."""

    def test_save_and_load_ascii_token(self, temp_db):
        """Сохранение и загрузка ASCII-токена."""
        import os

        token = "abc-123-token"
        save_session_token(token, "test-enc-agent", directory=Path.cwd())

        # Загружаем через load_session_token
        loaded = load_session_token(directory=Path.cwd())
        assert loaded == token

        # Очищаем переменные окружения
        os.environ.pop("SWARM_AGENT", None)

    def test_save_and_load_unicode_token(self, temp_db):
        """Сохранение и загрузка токена с unicode-символами."""
        import os

        token = "токен-сессии-юникод-12345"
        save_session_token(token, "uni-agent", directory=Path.cwd())

        loaded = load_session_token(directory=Path.cwd())
        assert loaded == token

        os.environ.pop("SWARM_AGENT", None)

    def test_session_file_is_utf8(self, temp_db):
        """Файл сессии записывается в UTF-8 кодировке."""
        import os

        token = "тест-utf8-кодировка"
        save_session_token(token, "utf8-agent", directory=Path.cwd())

        # Читаем файл напрямую в бинарном режиме
        session_path = Path.cwd() / SESSIONS_DIR / ".swarm_session_utf8-agent"
        raw = session_path.read_bytes()
        # Проверяем что содержимое — валидный UTF-8
        decoded = raw.decode("utf-8")
        assert decoded == token

        os.environ.pop("SWARM_AGENT", None)

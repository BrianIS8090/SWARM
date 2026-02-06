"""
Тесты модуля базы данных.
"""

import pytest
from pathlib import Path

from swarm.db import (
    init_database,
    find_db_path,
    register_agent,
    get_agent_by_session,
    get_all_agents,
    create_task,
    get_task,
    get_all_tasks,
    try_lock_file,
    get_file_lock,
    unlock_file,
    DB_FILENAME,
)
from swarm.models import AgentStatus, TaskStatus


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

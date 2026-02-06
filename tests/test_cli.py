"""
Интеграционные тесты CLI.
"""

import os
import pytest
from pathlib import Path
from typer.testing import CliRunner

from swarm.cli import app
from swarm.db import DB_FILENAME, SESSION_FILENAME


runner = CliRunner()


class TestInitCommand:
    """Тесты команды init."""
    
    def test_init_creates_database(self, tmp_path, monkeypatch):
        """Проверяет создание БД."""
        monkeypatch.chdir(tmp_path)
        
        result = runner.invoke(app, ["init"])
        
        assert result.exit_code == 0
        assert (tmp_path / DB_FILENAME).exists()
        assert "SWARM инициализирован успешно" in result.stdout
    
    def test_init_creates_skills_md(self, tmp_path, monkeypatch):
        """Проверяет создание SKILLS.md."""
        monkeypatch.chdir(tmp_path)
        
        result = runner.invoke(app, ["init"])
        
        assert result.exit_code == 0
        assert (tmp_path / "SKILLS.md").exists()
    
    def test_init_refuses_without_force(self, tmp_path, monkeypatch):
        """Проверяет отказ перезаписи без --force."""
        monkeypatch.chdir(tmp_path)
        
        # Первая инициализация
        runner.invoke(app, ["init"])
        
        # Попытка повторной
        result = runner.invoke(app, ["init"])
        
        assert result.exit_code == 1
        assert "уже существует" in result.stdout
    
    def test_init_force_recreates(self, tmp_path, monkeypatch):
        """Проверяет пересоздание с --force."""
        monkeypatch.chdir(tmp_path)
        
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init", "--force"])
        
        assert result.exit_code == 0
        assert "SWARM инициализирован успешно" in result.stdout


class TestTaskCommands:
    """Тесты команд управления задачами."""
    
    def test_task_add(self, tmp_path, monkeypatch):
        """Проверяет создание задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, [
            "task", "add",
            "--desc", "Тестовая задача",
            "--priority", "1",
        ])
        
        assert result.exit_code == 0
        assert "Задача #1 создана" in result.stdout
    
    def test_task_add_with_filters(self, tmp_path, monkeypatch):
        """Проверяет создание задачи с фильтрами."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, [
            "task", "add",
            "--desc", "Задача для архитектора",
            "--role", "architect",
            "--cli", "claude",
        ])
        
        assert result.exit_code == 0
        assert "role=architect" in result.stdout
        assert "cli=claude" in result.stdout
    
    def test_task_list_empty(self, tmp_path, monkeypatch):
        """Проверяет пустой список задач."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["task", "list"])
        
        assert result.exit_code == 0
        assert "Задач не найдено" in result.stdout
    
    def test_task_list_with_tasks(self, tmp_path, monkeypatch):
        """Проверяет список с задачами."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача 1", "--priority", "1"])
        runner.invoke(app, ["task", "add", "--desc", "Задача 2", "--priority", "2"])
        
        result = runner.invoke(app, ["task", "list"])
        
        assert result.exit_code == 0
        assert "Задача 1" in result.stdout
        assert "Задача 2" in result.stdout


class TestAgentCommands:
    """Тесты команд агентов."""
    
    def test_join_interactive(self, tmp_path, monkeypatch):
        """Проверяет регистрацию агента."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, [
            "join",
            "--cli", "claude",
            "--name", "test-agent",
            "--role", "developer",
        ])
        
        assert result.exit_code == 0
        assert "Зарегистрирован как агент #1" in result.stdout
        # Теперь файл сессии именуется по имени агента
        assert (tmp_path / ".swarm_session_test-agent").exists()
    
    def test_agents_empty(self, tmp_path, monkeypatch):
        """Проверяет пустой список агентов."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["agents"])
        
        assert result.exit_code == 0
        assert "агентов нет" in result.stdout
    
    def test_agents_with_registered(self, tmp_path, monkeypatch):
        """Проверяет список с агентами."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "alice", "--role", "developer"])
        
        result = runner.invoke(app, ["agents"])
        
        assert result.exit_code == 0
        assert "alice" in result.stdout
        assert "claude" in result.stdout
    
    def test_status_not_registered(self, tmp_path, monkeypatch):
        """Проверяет ошибку статуса без регистрации."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["status"])
        
        assert result.exit_code == 1
        assert "не зарегистрирован" in result.stdout
    
    def test_status_registered(self, tmp_path, monkeypatch):
        """Проверяет статус зарегистрированного агента."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "bob", "--role", "tester"])
        
        result = runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "bob" in result.stdout
        assert "tester" in result.stdout


class TestNextAndDone:
    """Тесты получения и завершения задач."""
    
    def test_next_no_tasks(self, tmp_path, monkeypatch):
        """Проверяет поведение при отсутствии задач."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])
        
        result = runner.invoke(app, ["next"])
        
        assert result.exit_code == 0
        assert "Нет подходящих задач" in result.stdout
    
    def test_next_gets_task(self, tmp_path, monkeypatch):
        """Проверяет получение задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Реализовать функцию", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])
        
        result = runner.invoke(app, ["next"])
        
        assert result.exit_code == 0
        assert "Задача #1" in result.stdout
        assert "Реализовать функцию" in result.stdout
    
    def test_done_completes_task(self, tmp_path, monkeypatch):
        """Проверяет завершение задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])
        runner.invoke(app, ["next"])
        
        result = runner.invoke(app, ["done", "--summary", "Готово"])
        
        assert result.exit_code == 0
        assert "Задача #1 завершена" in result.stdout
    
    def test_done_without_task_fails(self, tmp_path, monkeypatch):
        """Проверяет ошибку завершения без задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])
        
        result = runner.invoke(app, ["done", "--summary", "Что-то"])
        
        assert result.exit_code == 1
        assert "нет активной задачи" in result.stdout


class TestStartCommand:
    """Тесты команды start."""
    
    def test_start_no_agents(self, tmp_path, monkeypatch):
        """Проверяет start без агентов."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["start", "--all"])
        
        assert result.exit_code == 0
        assert "Нет зарегистрированных агентов" in result.stdout
    
    def test_start_all(self, tmp_path, monkeypatch):
        """Проверяет start --all."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent1", "--role", "developer"])
        
        # Очищаем переменные окружения для регистрации второго агента
        # (теперь у каждого агента свой файл .swarm_session_<имя>)
        if "SWARM_SESSION" in os.environ:
            del os.environ["SWARM_SESSION"]
        if "SWARM_AGENT" in os.environ:
            del os.environ["SWARM_AGENT"]
        runner.invoke(app, ["join", "--cli", "codex", "--name", "agent2", "--role", "tester"])
        
        result = runner.invoke(app, ["start", "--all"])
        
        assert result.exit_code == 0
        assert "2 агентов" in result.stdout


class TestLogsCommand:
    """Тесты команды logs."""
    
    def test_logs_empty(self, tmp_path, monkeypatch):
        """Проверяет пустой журнал."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["logs"])
        
        # При init создаётся только БД, событий пока нет
        # Но после join появятся
        assert result.exit_code == 0
    
    def test_logs_with_events(self, tmp_path, monkeypatch):
        """Проверяет журнал с событиями."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])
        
        result = runner.invoke(app, ["logs"])
        
        assert result.exit_code == 0
        # Текст может быть усечён в таблице, ищем часть
        assert "agent_register" in result.stdout or "зарегистрирован" in result.stdout

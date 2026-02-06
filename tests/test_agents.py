"""
Тесты управления агентами.
"""

import pytest
import os
from pathlib import Path

from swarm.db import (
    register_agent,
    get_agent_by_session,
    get_all_agents,
    update_agent_status,
    update_agent_heartbeat,
    save_session_token,
    load_session_token,
    get_current_agent,
)
from swarm.models import AgentStatus


class TestAgentRegistration:
    """Тесты регистрации агентов."""
    
    def test_register_unique_session_tokens(self, temp_db):
        """Проверяет уникальность токенов."""
        agent1 = register_agent("token-1", "claude", "agent1", "developer")
        
        # Попытка регистрации с тем же токеном должна вызвать ошибку
        with pytest.raises(Exception):
            register_agent("token-1", "claude", "agent2", "developer")
    
    def test_register_multiple_agents(self, temp_db):
        """Проверяет регистрацию нескольких агентов."""
        agents_data = [
            ("token-1", "claude", "alice", "architect"),
            ("token-2", "codex", "bob", "developer"),
            ("token-3", "gemini", "carol", "tester"),
        ]
        
        for token, cli, name, role in agents_data:
            register_agent(token, cli, name, role)
        
        agents = get_all_agents()
        
        assert len(agents) == 3
        assert {a.cli_type for a in agents} == {"claude", "codex", "gemini"}


class TestAgentStatus:
    """Тесты обновления статуса."""
    
    def test_update_status(self, sample_agent):
        """Проверяет обновление статуса."""
        update_agent_status(sample_agent.agent_id, AgentStatus.WORKING, task_id=1)
        
        agent = get_agent_by_session(sample_agent.session_token)
        
        assert agent.status == AgentStatus.WORKING
        assert agent.current_task_id == 1
    
    def test_update_heartbeat(self, sample_agent):
        """Проверяет обновление heartbeat."""
        original_hb = sample_agent.last_heartbeat
        
        import time
        time.sleep(0.1)  # Небольшая задержка
        
        update_agent_heartbeat(sample_agent.agent_id)
        
        agent = get_agent_by_session(sample_agent.session_token)
        
        # Heartbeat должен обновиться (сравниваем как строки для SQLite)
        assert agent.last_heartbeat >= original_hb


class TestSessionManagement:
    """Тесты управления сессией."""
    
    def test_save_and_load_session(self, temp_db):
        """Проверяет сохранение и загрузку токена."""
        token = "test-session-token-xyz"
        agent_name = "test-agent"
        
        save_session_token(token, agent_name)
        loaded = load_session_token()
        
        assert loaded == token
    
    def test_load_nonexistent_session(self, temp_db):
        """Проверяет загрузку несуществующей сессии."""
        # Очищаем переменные окружения
        if "SWARM_SESSION" in os.environ:
            del os.environ["SWARM_SESSION"]
        if "SWARM_AGENT" in os.environ:
            del os.environ["SWARM_AGENT"]
        
        # Удаляем файл сессии если есть
        session_path = Path.cwd() / ".swarm_session"
        if session_path.exists():
            session_path.unlink()
        
        loaded = load_session_token()
        
        assert loaded is None
    
    def test_get_current_agent(self, temp_db):
        """Проверяет получение текущего агента."""
        token = "current-agent-token"
        agent_name = "current"
        
        agent = register_agent(token, "claude", agent_name, "developer")
        save_session_token(token, agent_name)
        
        current = get_current_agent()
        
        assert current is not None
        assert current.agent_id == agent.agent_id
        assert current.name == "current"
    
    def test_get_current_agent_no_session(self, temp_db):
        """Проверяет поведение без сохранённой сессии."""
        # Очищаем переменные окружения
        if "SWARM_SESSION" in os.environ:
            del os.environ["SWARM_SESSION"]
        if "SWARM_AGENT" in os.environ:
            del os.environ["SWARM_AGENT"]
        
        # Удаляем файл сессии
        session_path = Path.cwd() / ".swarm_session"
        if session_path.exists():
            session_path.unlink()
        
        current = get_current_agent()
        
        assert current is None

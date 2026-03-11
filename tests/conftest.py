"""
Общие фикстуры для тестов SWARM.
"""

import os
import sys
from pathlib import Path

import pytest

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from swarm.db import init_database


@pytest.fixture
def temp_db(tmp_path):
    """
    Создаёт временную базу данных для тестов.

    Очищает переменные окружения SWARM_SESSION и SWARM_AGENT
    для изоляции тестов при параллельном запуске.
    Возвращает путь к директории с БД.
    """
    init_database(tmp_path)

    # Сохраняем текущую директорию
    original_cwd = os.getcwd()

    # Очищаем env-переменные для изоляции тестов
    old_session = os.environ.pop("SWARM_SESSION", None)
    old_agent = os.environ.pop("SWARM_AGENT", None)

    # Переходим в директорию с БД
    os.chdir(tmp_path)

    yield tmp_path

    # Возвращаемся
    os.chdir(original_cwd)

    # Восстанавливаем env-переменные
    if old_session is not None:
        os.environ["SWARM_SESSION"] = old_session
    else:
        os.environ.pop("SWARM_SESSION", None)
    if old_agent is not None:
        os.environ["SWARM_AGENT"] = old_agent
    else:
        os.environ.pop("SWARM_AGENT", None)


@pytest.fixture
def sample_agent(temp_db):
    """Создаёт тестового агента."""
    from swarm.db import register_agent
    
    agent = register_agent(
        session_token="test-token-123",
        cli_type="claude",
        name="test-agent",
        role="developer",
        pid=12345,
    )
    return agent


@pytest.fixture
def sample_task(temp_db):
    """Создаёт тестовую задачу."""
    from swarm.db import create_task
    
    task = create_task(
        description="Тестовая задача",
        priority=2,
    )
    return task

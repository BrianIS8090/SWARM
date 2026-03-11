"""
Тесты общего модуля commands/common.py.

Проверяет _check_agent: поиск агента по имени и обработку отсутствующего агента.
"""

import pytest

from swarm.commands.common import _check_agent
from swarm.db import register_agent


class TestCheckAgent:
  """Тесты функции _check_agent."""

  def test_check_agent_by_name(self, temp_db):
    """_check_agent возвращает агента при передаче корректного имени."""
    registered = register_agent(
      session_token="tok-common-1",
      cli_type="claude",
      name="agent-common",
      role="developer",
      pid=9999,
    )

    result = _check_agent(agent_name="agent-common")

    assert result.agent_id == registered.agent_id
    assert result.name == "agent-common"

  def test_check_agent_not_found(self, temp_db):
    """_check_agent бросает typer.Exit при несуществующем агенте."""
    with pytest.raises((SystemExit, RuntimeError)):
      _check_agent(agent_name="nonexistent-agent")

  def test_check_agent_no_session(self, temp_db, monkeypatch):
    """_check_agent бросает typer.Exit если нет сессии и имя не указано."""
    # Убираем переменные окружения, чтобы гарантировать отсутствие сессии
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)

    with pytest.raises((SystemExit, RuntimeError)):
      _check_agent(agent_name=None)

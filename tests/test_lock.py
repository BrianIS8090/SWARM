"""
Тесты для команд блокировки файлов (lock.py).

Включает тест КРИТ-2: при таймауте ожидания блокировки
статус агента НЕ должен оставаться WAITING.
"""

from unittest.mock import patch

from typer.testing import CliRunner

from swarm.cli import app
from swarm.db import get_agent_by_name

runner = CliRunner()


class TestLockTimeout:
  """Тесты таймаута блокировки (КРИТ-2)."""

  def test_lock_timeout_restores_agent_status(self, tmp_path, monkeypatch):
    """
    КРИТ-2: При таймауте ожидания блокировки статус агента
    должен быть восстановлен в WORKING, а не оставаться WAITING.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    # Создаём задачу и двух агентов
    runner.invoke(app, ["task", "add", "--desc", "Задача 1", "--priority", "1"])
    runner.invoke(app, ["task", "add", "--desc", "Задача 2", "--priority", "2"])

    # Первый агент захватывает файл
    runner.invoke(app, ["join", "--cli", "claude", "--name", "holder", "--role", "developer"])
    runner.invoke(app, ["next"])
    runner.invoke(app, ["lock", "shared.py"])

    # Второй агент пытается заблокировать тот же файл с маленьким таймаутом
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)
    runner.invoke(app, ["join", "--cli", "codex", "--name", "waiter", "--role", "developer"])
    runner.invoke(app, ["next"])

    # Патчим time.sleep чтобы не ждать реально, и ставим таймаут 0
    with patch("swarm.commands.lock.time.sleep"):
      result = runner.invoke(app, ["lock", "shared.py", "--timeout", "0", "--agent", "waiter"])

    assert result.exit_code == 1
    assert "Таймаут" in result.stdout

    # Проверяем что статус waiter НЕ WAITING
    agent = get_agent_by_name("waiter")
    assert agent is not None
    assert agent.status.value != "waiting", (
      f"Статус агента должен быть восстановлен из WAITING, но получен: {agent.status.value}"
    )
    # Статус должен быть WORKING (восстановлен)
    assert agent.status.value == "working"

  def test_lock_timeout_without_waiting_state(self, tmp_path, monkeypatch):
    """
    Если таймаут наступил до того как агент вошёл в состояние WAITING
    (timeout=0 и файл свободен — маловероятный сценарий),
    статус агента не должен измениться на WAITING.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
    runner.invoke(app, ["task", "add", "--desc", "Задача 2", "--priority", "2"])

    # Первый агент блокирует файл
    runner.invoke(app, ["join", "--cli", "claude", "--name", "blocker", "--role", "developer"])
    runner.invoke(app, ["next"])
    runner.invoke(app, ["lock", "file.py"])

    # Второй агент с таймаутом 0
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)
    runner.invoke(app, ["join", "--cli", "codex", "--name", "fast-agent", "--role", "developer"])
    runner.invoke(app, ["next"])

    with patch("swarm.commands.lock.time.sleep"):
      result = runner.invoke(app, ["lock", "file.py", "--timeout", "0", "--agent", "fast-agent"])

    assert result.exit_code == 1

    agent = get_agent_by_name("fast-agent")
    assert agent is not None
    # Статус не должен быть WAITING
    assert agent.status.value != "waiting"

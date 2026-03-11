"""
Тесты для команд терминальной оркестрации (terminal.py).

Включает тесты для:
- КРИТ-6: stop_command с fallback использует taskkill на Windows
- ВАЖ-10: при exclude-cli с total_launchable==0 статус НЕ LAUNCHED
- ВАЖ-9: явный layout mode из spec сохраняется
"""

import json
import sys
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from swarm.cli import app
from swarm.db import get_launch_sessions
from swarm.models import LaunchSessionStatus

runner = CliRunner()


def _make_spec_file(tmp_path, agents, layout_mode="mixed"):
  """Вспомогательная функция: создаёт spec JSON для тестов."""
  spec = {
    "version": 1,
    "working_directory": str(tmp_path),
    "approval_mode": "safe",
    "layout": {
      "mode": layout_mode,
      "max_panes_per_window": 4,
    },
    "agents": agents,
  }
  spec_path = tmp_path / "test-spec.json"
  spec_path.write_text(json.dumps(spec), encoding="utf-8")
  return spec_path


class TestStopCommandFallback:
  """Тесты КРИТ-6: stop_command fallback использует taskkill на Windows."""

  def test_stop_fallback_uses_taskkill_on_windows(self, tmp_path, monkeypatch):
    """
    КРИТ-6: При fallback через БД PID, на Windows должен использоваться
    taskkill /T /F вместо os.kill для завершения дерева процессов.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    from swarm.commands import terminal as terminal_cmd

    monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

    # Создаём launch session через dry-run
    spec_path = _make_spec_file(tmp_path, [
      {"cli": "claude", "name": "stop-fb-1", "role": "developer", "window": 1, "pane": 1},
      {"cli": "codex", "name": "stop-fb-2", "role": "developer", "window": 1, "pane": 2},
    ])

    runner.invoke(app, ["terminal", "launch", "--spec", str(spec_path), "--yes", "--dry-run"])

    sessions = get_launch_sessions()
    assert len(sessions) == 1
    session_id = sessions[0].session_id

    # Записываем PID в БД для агентов (имитируем запуск)
    from swarm.db import update_launch_agent_status
    from swarm.models import LaunchRegistrationStatus

    update_launch_agent_status(session_id, "stop-fb-1", LaunchRegistrationStatus.LAUNCHED, terminal_pid=99991)
    update_launch_agent_status(session_id, "stop-fb-2", LaunchRegistrationStatus.LAUNCHED, terminal_pid=99992)

    # Мокаем os.name = "nt" и subprocess.run
    mock_subprocess_run = MagicMock()
    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setattr(terminal_cmd.subprocess, "run", mock_subprocess_run)

    result = runner.invoke(app, ["terminal", "stop", "--session", session_id])

    assert result.exit_code == 0
    assert "остановлена" in result.stdout.lower()

    # Проверяем, что taskkill был вызван для каждого PID
    taskkill_calls = [
      call for call in mock_subprocess_run.call_args_list
      if call[0][0][0] == "taskkill"
    ]
    assert len(taskkill_calls) >= 2, (
      f"Ожидалось минимум 2 вызова taskkill, получено: {len(taskkill_calls)}"
    )

    # Проверяем что вызовы содержат /T и /F (дерево процессов)
    for call in taskkill_calls:
      cmd_args = call[0][0]
      assert "/T" in cmd_args, f"taskkill должен содержать /T: {cmd_args}"
      assert "/F" in cmd_args, f"taskkill должен содержать /F: {cmd_args}"

  @pytest.mark.skipif(sys.platform == "win32", reason="PosixPath недоступен на Windows")
  def test_stop_fallback_uses_os_kill_on_linux(self, tmp_path, monkeypatch):
    """
    На не-Windows системах fallback должен использовать os.kill.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    from swarm.commands import terminal as terminal_cmd

    monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

    spec_path = _make_spec_file(tmp_path, [
      {"cli": "claude", "name": "stop-lnx-1", "role": "developer", "window": 1, "pane": 1},
      {"cli": "codex", "name": "stop-lnx-2", "role": "developer", "window": 1, "pane": 2},
    ])

    runner.invoke(app, ["terminal", "launch", "--spec", str(spec_path), "--yes", "--dry-run"])

    sessions = get_launch_sessions()
    session_id = sessions[0].session_id

    from swarm.db import update_launch_agent_status
    from swarm.models import LaunchRegistrationStatus

    update_launch_agent_status(session_id, "stop-lnx-1", LaunchRegistrationStatus.LAUNCHED, terminal_pid=88881)

    # Мокаем os.name = "posix" и os.kill
    monkeypatch.setattr("os.name", "posix")
    mock_os_kill = MagicMock()
    monkeypatch.setattr(terminal_cmd.os, "kill", mock_os_kill)

    result = runner.invoke(app, ["terminal", "stop", "--session", session_id])

    assert result.exit_code == 0
    # Проверяем, что os.kill был вызван
    assert mock_os_kill.called, "На не-Windows должен использоваться os.kill"


class TestExcludeCliStatus:
  """Тесты ВАЖ-10: при exclude-cli с total_launchable==0 статус НЕ LAUNCHED."""

  def test_all_excluded_status_not_launched(self, tmp_path, monkeypatch):
    """
    ВАЖ-10: Если все агенты исключены через --exclude-cli,
    статус launch session НЕ должен быть LAUNCHED.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    from swarm.commands import terminal as terminal_cmd

    monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

    # Все агенты одного CLI-типа, который мы исключим
    spec_path = _make_spec_file(tmp_path, [
      {"cli": "claude", "name": "excl-1", "role": "developer", "window": 1, "pane": 1},
      {"cli": "claude", "name": "excl-2", "role": "developer", "window": 1, "pane": 2},
    ])

    # Мокаем launch_layout чтобы он не запускал реальные терминалы
    monkeypatch.setattr(terminal_cmd, "launch_layout", lambda *a, **kw: {})

    result = runner.invoke(
      app,
      ["terminal", "launch", "--spec", str(spec_path), "--exclude-cli", "claude", "--yes"],
    )

    assert result.exit_code == 0

    sessions = get_launch_sessions()
    assert len(sessions) == 1
    session = sessions[0]
    # Статус НЕ должен быть LAUNCHED — ничего не запущено
    assert session.status != LaunchSessionStatus.LAUNCHED, (
      f"Статус должен быть отличен от LAUNCHED при total_launchable==0, получен: {session.status.value}"
    )


class TestLayoutModePreservation:
  """Тесты ВАЖ-9: явный layout mode из spec сохраняется при запуске."""

  def test_explicit_layout_mode_preserved(self, tmp_path, monkeypatch):
    """
    ВАЖ-9: Если в spec задан layout.mode='mixed', при создании launch_spec
    для launchable агентов он должен сохраниться, а не замениться на auto.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    from swarm.commands import terminal as terminal_cmd

    monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

    # Spec с mode="mixed" и 2 агента (mixed должен сохраниться)
    spec_path = _make_spec_file(tmp_path, [
      {"cli": "claude", "name": "layout-1", "role": "developer", "window": 1, "pane": 1},
      {"cli": "codex", "name": "layout-2", "role": "developer", "window": 1, "pane": 2},
    ], layout_mode="mixed")

    # Перехватываем вызов launch_layout и проверяем переданный spec
    captured_specs = []

    def mock_launch_layout(spec, prompt_map, session_id=None):
      captured_specs.append(spec)
      return {}

    monkeypatch.setattr(terminal_cmd, "launch_layout", mock_launch_layout)

    # Исключаем codex — остаётся 1 агент, auto_layout вернул бы "single"
    result = runner.invoke(
      app,
      ["terminal", "launch", "--spec", str(spec_path), "--exclude-cli", "codex", "--yes"],
    )

    assert result.exit_code == 0
    assert len(captured_specs) == 1
    # Должен быть "mixed" (из spec), а не "single" (из auto)
    assert captured_specs[0].layout.mode == "mixed", (
      f"Ожидался mode='mixed' из spec, получен: {captured_specs[0].layout.mode}"
    )

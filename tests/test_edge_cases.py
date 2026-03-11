"""
Тесты граничных случаев для lock, task и agents.
"""

from typer.testing import CliRunner

from swarm.cli import app
from swarm.db import (
  assign_task_to_agent,
  claim_next_task,
  complete_task,
  create_task,
  get_agent_by_session,
  get_file_lock,
  register_agent,
  try_lock_file,
  unlock_file,
)
from swarm.models import TaskStatus

runner = CliRunner()


# ============================================================
# Lock edge cases (через db-слой)
# ============================================================


class TestLockEdgeCases:
  """Граничные случаи блокировок файлов."""

  def test_unlock_foreign_lock_denied(self, temp_db):
    """Разблокировка чужой блокировки должна быть отклонена."""
    agent1 = register_agent("tok-le1", "claude", "owner", "developer")
    agent2 = register_agent("tok-le2", "codex", "stranger", "developer")
    task = create_task("Задача с блокировкой")

    # Первый агент блокирует файл
    assert try_lock_file(agent1.agent_id, task.task_id, "secret.py") is True

    # Второй агент пытается разблокировать — должен получить отказ
    result = unlock_file("secret.py", agent_id=agent2.agent_id)
    assert result is False

    # Блокировка осталась у первого агента
    lock = get_file_lock("secret.py")
    assert lock is not None
    assert lock.locked_by == agent1.agent_id

  def test_lock_same_file_twice_by_same_agent_is_idempotent(self, temp_db):
    """Повторная блокировка того же файла тем же агентом — идемпотентна."""
    agent = register_agent("tok-le3", "claude", "repeat-locker", "developer")
    task = create_task("Задача")

    # Первая блокировка
    assert try_lock_file(agent.agent_id, task.task_id, "same.py") is True

    # Повторная блокировка того же файла — возвращает True (уже заблокирован мной)
    assert try_lock_file(agent.agent_id, task.task_id, "same.py") is True

    # Файл всё ещё заблокирован
    lock = get_file_lock("same.py")
    assert lock is not None
    assert lock.locked_by == agent.agent_id

  def test_lock_different_file_while_holding_lock(self, temp_db):
    """Попытка заблокировать второй файл, пока первый заблокирован — отказ."""
    agent = register_agent("tok-le4", "claude", "greedy", "developer")
    task = create_task("Задача")

    assert try_lock_file(agent.agent_id, task.task_id, "first.py") is True
    # Второй файл — должен быть отказ (ограничение: одна блокировка на агента)
    assert try_lock_file(agent.agent_id, task.task_id, "second.py") is False


# ============================================================
# Lock edge cases (через CLI)
# ============================================================


class TestLockUnlockCLIEdgeCases:
  """Граничные случаи lock/unlock через CLI."""

  def test_unlock_foreign_lock_via_cli(self, tmp_path, monkeypatch):
    """Через CLI агент не может разблокировать чужой файл."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    # Создаём задачу и первого агента
    runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
    runner.invoke(app, ["join", "--cli", "claude", "--name", "locker", "--role", "developer"])
    runner.invoke(app, ["next"])
    runner.invoke(app, ["lock", "shared.py"])

    # Очищаем сессию первого агента
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)

    # Регистрируем второго агента
    runner.invoke(app, ["join", "--cli", "codex", "--name", "intruder", "--role", "developer"])

    # Второй агент пытается разблокировать файл без --force
    result = runner.invoke(app, ["unlock", "--file", "shared.py"])

    # Должен быть отказ (exit_code=1) — файл заблокирован другим агентом
    assert result.exit_code == 1

  def test_lock_idempotent_via_cli(self, tmp_path, monkeypatch):
    """Повторная блокировка того же файла через CLI — идемпотентна."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
    runner.invoke(app, ["join", "--cli", "claude", "--name", "repeat", "--role", "developer"])
    runner.invoke(app, ["next"])

    # Первая блокировка
    result1 = runner.invoke(app, ["lock", "file.py"])
    assert result1.exit_code == 0

    # Повторная блокировка того же файла
    result2 = runner.invoke(app, ["lock", "file.py"])
    assert result2.exit_code == 0
    assert "уже заблокирован вами" in result2.stdout


# ============================================================
# Task edge cases (через CLI)
# ============================================================


class TestTaskCLIEdgeCases:
  """Граничные случаи задач через CLI."""

  def test_task_add_priority_zero(self, tmp_path, monkeypatch):
    """Приоритет 0 — невалидный, должна быть ошибка."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result = runner.invoke(
      app, ["task", "add", "--desc", "Задача", "--priority", "0"]
    )

    assert result.exit_code == 1
    assert "Приоритет должен быть от 1 до 5" in result.stdout

  def test_task_add_priority_six(self, tmp_path, monkeypatch):
    """Приоритет 6 — невалидный, должна быть ошибка."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result = runner.invoke(
      app, ["task", "add", "--desc", "Задача", "--priority", "6"]
    )

    assert result.exit_code == 1
    assert "Приоритет должен быть от 1 до 5" in result.stdout

  def test_task_add_valid_priority_boundaries(self, tmp_path, monkeypatch):
    """Приоритеты 1 и 5 — граничные допустимые значения."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result1 = runner.invoke(
      app, ["task", "add", "--desc", "Минимальный приоритет", "--priority", "1"]
    )
    assert result1.exit_code == 0

    result5 = runner.invoke(
      app, ["task", "add", "--desc", "Максимальный приоритет", "--priority", "5"]
    )
    assert result5.exit_code == 0

  def test_task_add_with_nonexistent_depends_on(self, tmp_path, monkeypatch):
    """Зависимость от несуществующей задачи вызывает ошибку."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result = runner.invoke(
      app, ["task", "add", "--desc", "Зависимая", "--depends-on", "999"]
    )

    assert result.exit_code == 1
    assert "не найдена" in result.stdout

  def test_task_assign_to_done_task(self, tmp_path, monkeypatch):
    """Назначение задачи, которая уже завершена (done)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["task", "add", "--desc", "Для завершения", "--priority", "1"])

    # Закрываем задачу принудительно
    runner.invoke(app, ["task", "close", "1", "--reason", "Закрыта"])

    # Пытаемся назначить завершённую задачу
    result = runner.invoke(app, ["task", "assign", "1", "--agent", "worker-1"])

    # Должна вернуть 0, но сообщить что задача уже завершена
    assert result.exit_code == 0
    assert "уже завершена" in result.stdout

  def test_task_assign_to_in_progress_task(self, tmp_path, monkeypatch):
    """Назначение задачи, которая уже выполняется (in_progress)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["task", "add", "--desc", "В работе", "--priority", "1"])
    runner.invoke(app, ["join", "--cli", "claude", "--name", "busy-agent", "--role", "developer"])
    runner.invoke(app, ["next"])

    # Убираем сессию агента, чтобы стать Лидером
    monkeypatch.delenv("SWARM_AGENT", raising=False)

    # Пытаемся назначить задачу in_progress
    result = runner.invoke(app, ["task", "assign", "1", "--agent", "other-agent"])

    assert result.exit_code == 0
    assert "уже выполняется" in result.stdout


# ============================================================
# Task edge cases (через db-слой)
# ============================================================


class TestTaskDBEdgeCases:
  """Граничные случаи задач на уровне БД."""

  def test_assign_done_task_returns_false(self, temp_db):
    """assign_task_to_agent возвращает False для завершённой задачи."""
    agent = register_agent("tok-te1", "claude", "worker-done", "developer")
    task = create_task("Задача для завершения")

    # Захватываем и завершаем
    claim_next_task(agent)
    agent = get_agent_by_session("tok-te1")
    complete_task(agent, "Готово")

    # Проверяем статус задачи
    from swarm.db import get_task
    done_task = get_task(task.task_id)
    assert done_task.status == TaskStatus.DONE

    # Пытаемся назначить завершённую задачу
    result = assign_task_to_agent(task.task_id, "some-agent")
    assert result is False

  def test_assign_in_progress_task_returns_false(self, temp_db):
    """assign_task_to_agent возвращает False для задачи in_progress."""
    agent = register_agent("tok-te2", "claude", "busy-worker", "developer")
    task = create_task("Задача в работе")

    # Захватываем задачу (переходит в in_progress)
    claimed = claim_next_task(agent)
    assert claimed is not None

    # Пытаемся назначить другому агенту
    result = assign_task_to_agent(task.task_id, "another-agent")
    assert result is False


# ============================================================
# Agents edge cases (через CLI)
# ============================================================


class TestAgentsCLIEdgeCases:
  """Граничные случаи команды agents через CLI."""

  def test_agents_cleanup_force(self, tmp_path, monkeypatch):
    """agents --cleanup --force удаляет всех агентов."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["join", "--cli", "claude", "--name", "agent-a", "--role", "developer"])

    # Очищаем сессию для регистрации второго
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)
    runner.invoke(app, ["join", "--cli", "codex", "--name", "agent-b", "--role", "tester"])

    # Очищаем сессию чтобы команда agents не привязывалась к агенту
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)

    # Принудительная очистка
    result = runner.invoke(app, ["agents", "--cleanup", "--force"])

    assert result.exit_code == 0
    assert "Принудительно удалено агентов: 2" in result.stdout
    # После удаления список пуст
    assert "агентов нет" in result.stdout

  def test_agents_cleanup_no_dead(self, tmp_path, monkeypatch):
    """agents --cleanup без мёртвых агентов ничего не удаляет."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["join", "--cli", "claude", "--name", "alive", "--role", "developer"])

    # Очищаем сессию чтобы не привязываться к агенту
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)

    result = runner.invoke(app, ["agents", "--cleanup"])

    assert result.exit_code == 0
    # Агент жив (свежий heartbeat), не должен быть удалён
    assert "alive" in result.stdout

  def test_agents_cleanup_force_releases_tasks(self, tmp_path, monkeypatch):
    """agents --cleanup --force освобождает задачи in_progress."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
    runner.invoke(app, ["join", "--cli", "claude", "--name", "cleaner", "--role", "developer"])
    runner.invoke(app, ["next"])

    # Очищаем сессию
    monkeypatch.delenv("SWARM_AGENT", raising=False)
    monkeypatch.delenv("SWARM_SESSION", raising=False)

    # Проверяем что задача in_progress
    from swarm.db import get_task
    task_before = get_task(1)
    assert task_before.status == TaskStatus.IN_PROGRESS

    # Принудительная очистка
    result = runner.invoke(app, ["agents", "--cleanup", "--force"])
    assert result.exit_code == 0

    # Задача должна стать failed
    task_after = get_task(1)
    assert task_after.status == TaskStatus.FAILED
    assert task_after.assigned_to is None

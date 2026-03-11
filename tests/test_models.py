"""
Тесты моделей данных SWARM.

Проверяет безопасный парсинг enum-значений из БД через from_row().
"""

from datetime import datetime

from swarm.models import (
  Agent,
  AgentStatus,
  EventType,
  FileLock,
  LaunchRegistrationStatus,
  LaunchSession,
  LaunchSessionAgent,
  LaunchSessionStatus,
  Task,
  TaskLogEntry,
  TaskStatus,
  _safe_enum,
)

# --- Вспомогательные фабрики для создания dict-строк БД ---

def _agent_row(**overrides):
  """Возвращает словарь, имитирующий строку из таблицы agents."""
  row = {
    "agent_id": 1,
    "session_token": "tok-abc",
    "cli_type": "claude",
    "name": "test-agent",
    "role": "developer",
    "status": "idle",
    "current_task_id": None,
    "registered_at": "2025-01-01T00:00:00",
    "last_heartbeat": "2025-01-01T00:00:00",
    "pid": 1234,
  }
  row.update(overrides)
  return row


def _task_row(**overrides):
  """Возвращает словарь, имитирующий строку из таблицы tasks."""
  row = {
    "task_id": 1,
    "description": "Тестовая задача",
    "priority": 2,
    "target_cli": None,
    "target_name": None,
    "target_role": None,
    "status": "pending",
    "assigned_to": None,
    "depends_on": None,
    "summary": None,
    "created_at": "2025-01-01T00:00:00",
    "started_at": None,
    "completed_at": None,
  }
  row.update(overrides)
  return row


def _log_entry_row(**overrides):
  """Возвращает словарь, имитирующий строку из таблицы task_log."""
  row = {
    "log_id": 1,
    "task_id": None,
    "agent_id": None,
    "event": "task_started",
    "message": "Задача начата",
    "timestamp": "2025-01-01T00:00:00",
  }
  row.update(overrides)
  return row


def _file_lock_row(**overrides):
  """Возвращает словарь, имитирующий строку из таблицы file_locks."""
  row = {
    "lock_id": 1,
    "file_path": "src/main.py",
    "locked_by": 1,
    "task_id": 1,
    "locked_at": "2025-01-01T00:00:00",
  }
  row.update(overrides)
  return row


def _launch_session_row(**overrides):
  """Возвращает словарь, имитирующий строку из таблицы launch_sessions."""
  row = {
    "session_id": "ls-001",
    "created_at": "2025-01-01T00:00:00",
    "working_directory": "/tmp/project",
    "approval_mode": "safe",
    "layout_mode": "single",
    "requested_agent_count": 2,
    "status": "planned",
    "created_by": "orchestrator",
  }
  row.update(overrides)
  return row


def _launch_session_agent_row(**overrides):
  """Возвращает словарь, имитирующий строку из таблицы launch_session_agents."""
  row = {
    "id": 1,
    "session_id": "ls-001",
    "cli_type": "claude",
    "agent_name": "dev-1",
    "agent_role": "developer",
    "window_index": 0,
    "pane_index": 0,
    "launcher_profile": "claude-safe",
    "bootstrap_prompt": "prompt",
    "registration_status": "planned",
    "registered_agent_id": None,
    "terminal_pid": None,
  }
  row.update(overrides)
  return row


# --- Тесты вспомогательной функции _safe_enum ---

class TestSafeEnum:
  """Тесты безопасного парсинга enum-значений."""

  def test_valid_value(self):
    """Валидное значение создаёт корректный enum."""
    assert _safe_enum(AgentStatus, "idle") == AgentStatus.IDLE

  def test_unknown_value_returns_unknown(self):
    """Неизвестное значение возвращает UNKNOWN вместо исключения."""
    result = _safe_enum(AgentStatus, "nonexistent_status")
    assert result == AgentStatus.UNKNOWN

  def test_all_enums_have_unknown(self):
    """Все enum-классы моделей содержат значение UNKNOWN."""
    for enum_cls in [AgentStatus, TaskStatus, EventType, LaunchSessionStatus, LaunchRegistrationStatus]:
      assert hasattr(enum_cls, "UNKNOWN"), f"{enum_cls.__name__} не имеет UNKNOWN"
      assert enum_cls.UNKNOWN.value == "unknown"


# --- Тесты Agent.from_row ---

class TestAgentFromRow:
  """Тесты десериализации Agent из строки БД."""

  def test_valid_status(self):
    """Валидный статус агента парсится корректно."""
    agent = Agent.from_row(_agent_row(status="working"))
    assert agent.status == AgentStatus.WORKING
    assert agent.name == "test-agent"
    assert agent.cli_type == "claude"

  def test_unknown_status(self):
    """Неизвестный статус агента не бросает ValueError."""
    agent = Agent.from_row(_agent_row(status="deprecated_status"))
    assert agent.status == AgentStatus.UNKNOWN

  def test_datetime_parsing(self):
    """Временные поля парсятся в datetime."""
    agent = Agent.from_row(_agent_row())
    assert isinstance(agent.registered_at, datetime)
    assert isinstance(agent.last_heartbeat, datetime)


# --- Тесты Task.from_row ---

class TestTaskFromRow:
  """Тесты десериализации Task из строки БД."""

  def test_valid_status(self):
    """Валидный статус задачи парсится корректно."""
    task = Task.from_row(_task_row(status="in_progress"))
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.description == "Тестовая задача"

  def test_unknown_status(self):
    """Неизвестный статус задачи не бросает ValueError."""
    task = Task.from_row(_task_row(status="archived"))
    assert task.status == TaskStatus.UNKNOWN

  def test_nullable_fields(self):
    """Необязательные поля корректно принимают None."""
    task = Task.from_row(_task_row())
    assert task.target_cli is None
    assert task.assigned_to is None
    assert task.started_at is None


# --- Тесты TaskLogEntry.from_row ---

class TestTaskLogEntryFromRow:
  """Тесты десериализации TaskLogEntry из строки БД."""

  def test_valid_event(self):
    """Валидный тип события парсится корректно."""
    entry = TaskLogEntry.from_row(_log_entry_row(event="error"))
    assert entry.event == EventType.ERROR

  def test_unknown_event(self):
    """Неизвестный тип события не бросает ValueError."""
    entry = TaskLogEntry.from_row(_log_entry_row(event="future_event_type"))
    assert entry.event == EventType.UNKNOWN

  def test_message_preserved(self):
    """Сообщение лога сохраняется без изменений."""
    entry = TaskLogEntry.from_row(_log_entry_row(message="Тест"))
    assert entry.message == "Тест"


# --- Тесты FileLock.from_row ---

class TestFileLockFromRow:
  """Тесты десериализации FileLock из строки БД."""

  def test_valid_row(self):
    """Корректная строка БД создаёт валидный объект."""
    lock = FileLock.from_row(_file_lock_row())
    assert lock.file_path == "src/main.py"
    assert lock.locked_by == 1
    assert isinstance(lock.locked_at, datetime)


# --- Тесты LaunchSession.from_row ---

class TestLaunchSessionFromRow:
  """Тесты десериализации LaunchSession из строки БД."""

  def test_valid_status(self):
    """Валидный статус launch-сессии парсится корректно."""
    session = LaunchSession.from_row(_launch_session_row(status="approved"))
    assert session.status == LaunchSessionStatus.APPROVED

  def test_unknown_status(self):
    """Неизвестный статус launch-сессии не бросает ValueError."""
    session = LaunchSession.from_row(_launch_session_row(status="cancelled"))
    assert session.status == LaunchSessionStatus.UNKNOWN


# --- Тесты LaunchSessionAgent.from_row ---

class TestLaunchSessionAgentFromRow:
  """Тесты десериализации LaunchSessionAgent из строки БД."""

  def test_valid_registration_status(self):
    """Валидный статус регистрации парсится корректно."""
    agent = LaunchSessionAgent.from_row(_launch_session_agent_row(registration_status="registered"))
    assert agent.registration_status == LaunchRegistrationStatus.REGISTERED

  def test_unknown_registration_status(self):
    """Неизвестный статус регистрации не бросает ValueError."""
    agent = LaunchSessionAgent.from_row(_launch_session_agent_row(registration_status="expired"))
    assert agent.registration_status == LaunchRegistrationStatus.UNKNOWN

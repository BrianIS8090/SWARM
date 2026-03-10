"""
Модели данных для SWARM.

Dataclass-модели для агентов, задач, блокировок и событий лога.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Статусы агента."""

    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    DONE = "done"


class TaskStatus(str, Enum):
    """Статусы задачи."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


class EventType(str, Enum):
    """Типы событий для лога."""

    TASK_STARTED = "task_started"
    TASK_DONE = "task_done"
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_FORCE_CLOSED = "task_force_closed"
    FILE_LOCKED = "file_locked"
    FILE_UNLOCKED = "file_unlocked"
    WAITING_FOR_LOCK = "waiting_for_lock"
    ERROR = "error"
    AGENT_REGISTERED = "agent_registered"
    AGENT_STARTED = "agent_started"
    AGENT_CLEANUP = "agent_cleanup"
    LAUNCH_SESSION_CREATED = "launch_session_created"
    LAUNCH_SESSION_APPROVED = "launch_session_approved"
    LAUNCH_STARTED = "launch_started"
    LAUNCH_AGENT_STARTED = "launch_agent_started"
    LAUNCH_AGENT_REGISTERED = "launch_agent_registered"
    LAUNCH_AGENT_FAILED = "launch_agent_failed"
    LAUNCH_SESSION_COMPLETED = "launch_session_completed"
    LAUNCH_SESSION_STOPPED = "launch_session_stopped"


class LaunchSessionStatus(str, Enum):
    """Статусы сессии запуска терминалов."""

    PLANNED = "planned"
    APPROVED = "approved"
    LAUNCHED = "launched"
    PARTIALLY_REGISTERED = "partially_registered"
    REGISTERED = "registered"
    FAILED = "failed"
    STOPPED = "stopped"


class LaunchRegistrationStatus(str, Enum):
    """Статусы регистрации агента внутри launch-сессии."""

    PLANNED = "planned"
    LAUNCHED = "launched"
    REGISTERED = "registered"
    FAILED = "failed"


def _parse_dt(value):
    """Преобразует строку времени из БД в datetime."""

    if value is None:
        return None
    return datetime.fromisoformat(value) if isinstance(value, str) else value


@dataclass
class Agent:
    """Модель агента."""

    agent_id: int
    session_token: str
    cli_type: str
    name: str
    role: str
    status: AgentStatus
    current_task_id: int | None
    registered_at: datetime
    last_heartbeat: datetime
    pid: int | None = None

    @classmethod
    def from_row(cls, row) -> "Agent":
        """Создать агента из строки БД (sqlite3.Row или dict-like)."""
        return cls(
            agent_id=row["agent_id"],
            session_token=row["session_token"],
            cli_type=row["cli_type"],
            name=row["name"],
            role=row["role"],
            status=AgentStatus(row["status"]),
            current_task_id=row["current_task_id"],
            registered_at=_parse_dt(row["registered_at"]),
            last_heartbeat=_parse_dt(row["last_heartbeat"]),
            pid=row["pid"],
        )


@dataclass
class Task:
    """Модель задачи."""

    task_id: int
    description: str
    priority: int
    target_cli: str | None
    target_name: str | None
    target_role: str | None
    status: TaskStatus
    assigned_to: int | None
    depends_on: int | None
    summary: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_row(cls, row) -> "Task":
        """Создать задачу из строки БД (sqlite3.Row или dict-like)."""
        return cls(
            task_id=row["task_id"],
            description=row["description"],
            priority=row["priority"],
            target_cli=row["target_cli"],
            target_name=row["target_name"],
            target_role=row["target_role"],
            status=TaskStatus(row["status"]),
            assigned_to=row["assigned_to"],
            depends_on=row["depends_on"],
            summary=row["summary"],
            created_at=_parse_dt(row["created_at"]),
            started_at=_parse_dt(row["started_at"]),
            completed_at=_parse_dt(row["completed_at"]),
        )


@dataclass
class FileLock:
    """Модель блокировки файла."""

    lock_id: int
    file_path: str
    locked_by: int
    task_id: int
    locked_at: datetime

    @classmethod
    def from_row(cls, row) -> "FileLock":
        """Создать блокировку из строки БД (sqlite3.Row или dict-like)."""
        return cls(
            lock_id=row["lock_id"],
            file_path=row["file_path"],
            locked_by=row["locked_by"],
            task_id=row["task_id"],
            locked_at=_parse_dt(row["locked_at"]),
        )


@dataclass
class TaskLogEntry:
    """Запись в логе задач."""

    log_id: int
    task_id: int | None
    agent_id: int | None
    event: EventType
    message: str | None
    timestamp: datetime

    @classmethod
    def from_row(cls, row) -> "TaskLogEntry":
        """Создать запись лога из строки БД (sqlite3.Row или dict-like)."""
        return cls(
            log_id=row["log_id"],
            task_id=row["task_id"],
            agent_id=row["agent_id"],
            event=EventType(row["event"]),
            message=row["message"],
            timestamp=_parse_dt(row["timestamp"]),
        )


@dataclass
class LaunchSession:
    """Сессия запуска терминальных агентов."""

    session_id: str
    created_at: datetime
    working_directory: str
    approval_mode: str
    layout_mode: str
    requested_agent_count: int
    status: LaunchSessionStatus
    created_by: str

    @classmethod
    def from_row(cls, row) -> "LaunchSession":
        """Создать launch-сессию из строки БД."""

        return cls(
            session_id=row["session_id"],
            created_at=_parse_dt(row["created_at"]),
            working_directory=row["working_directory"],
            approval_mode=row["approval_mode"],
            layout_mode=row["layout_mode"],
            requested_agent_count=row["requested_agent_count"],
            status=LaunchSessionStatus(row["status"]),
            created_by=row["created_by"],
        )


@dataclass
class LaunchSessionAgent:
    """Агент, входящий в launch-сессию."""

    id: int
    session_id: str
    cli_type: str
    agent_name: str
    agent_role: str
    window_index: int | None
    pane_index: int | None
    launcher_profile: str
    bootstrap_prompt: str
    registration_status: LaunchRegistrationStatus
    registered_agent_id: int | None
    terminal_pid: int | None

    @classmethod
    def from_row(cls, row) -> "LaunchSessionAgent":
        """Создать launch-агента из строки БД."""

        return cls(
            id=row["id"],
            session_id=row["session_id"],
            cli_type=row["cli_type"],
            agent_name=row["agent_name"],
            agent_role=row["agent_role"],
            window_index=row["window_index"],
            pane_index=row["pane_index"],
            launcher_profile=row["launcher_profile"],
            bootstrap_prompt=row["bootstrap_prompt"],
            registration_status=LaunchRegistrationStatus(row["registration_status"]),
            registered_agent_id=row["registered_agent_id"],
            terminal_pid=row["terminal_pid"],
        )

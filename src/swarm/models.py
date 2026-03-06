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
            registered_at=datetime.fromisoformat(row["registered_at"]) if isinstance(row["registered_at"], str) else row["registered_at"],
            last_heartbeat=datetime.fromisoformat(row["last_heartbeat"]) if isinstance(row["last_heartbeat"], str) else row["last_heartbeat"],
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
        def parse_dt(val):
            if val is None:
                return None
            return datetime.fromisoformat(val) if isinstance(val, str) else val

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
            created_at=parse_dt(row["created_at"]),
            started_at=parse_dt(row["started_at"]),
            completed_at=parse_dt(row["completed_at"]),
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
            locked_at=datetime.fromisoformat(row["locked_at"]) if isinstance(row["locked_at"], str) else row["locked_at"],
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
            timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
        )

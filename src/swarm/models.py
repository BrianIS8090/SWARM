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


class EventType(str, Enum):
    """Типы событий для лога."""
    TASK_STARTED = "task_started"
    TASK_DONE = "task_done"
    FILE_LOCKED = "file_locked"
    FILE_UNLOCKED = "file_unlocked"
    WAITING_FOR_LOCK = "waiting_for_lock"
    ERROR = "error"
    AGENT_REGISTERED = "agent_registered"
    AGENT_STARTED = "agent_started"


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
    def from_row(cls, row: tuple) -> "Agent":
        """Создать агента из строки БД."""
        return cls(
            agent_id=row[0],
            session_token=row[1],
            cli_type=row[2],
            name=row[3],
            role=row[4],
            status=AgentStatus(row[5]),
            current_task_id=row[6],
            registered_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
            last_heartbeat=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
            pid=row[9],
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
    def from_row(cls, row: tuple) -> "Task":
        """Создать задачу из строки БД."""
        def parse_dt(val):
            if val is None:
                return None
            return datetime.fromisoformat(val) if isinstance(val, str) else val

        return cls(
            task_id=row[0],
            description=row[1],
            priority=row[2],
            target_cli=row[3],
            target_name=row[4],
            target_role=row[5],
            status=TaskStatus(row[6]),
            assigned_to=row[7],
            depends_on=row[8],
            summary=row[9],
            created_at=parse_dt(row[10]),
            started_at=parse_dt(row[11]),
            completed_at=parse_dt(row[12]),
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
    def from_row(cls, row: tuple) -> "FileLock":
        """Создать блокировку из строки БД."""
        return cls(
            lock_id=row[0],
            file_path=row[1],
            locked_by=row[2],
            task_id=row[3],
            locked_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
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
    def from_row(cls, row: tuple) -> "TaskLogEntry":
        """Создать запись лога из строки БД."""
        return cls(
            log_id=row[0],
            task_id=row[1],
            agent_id=row[2],
            event=EventType(row[3]),
            message=row[4],
            timestamp=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
        )

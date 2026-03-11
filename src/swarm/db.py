"""
Модуль работы с базой данных SWARM.

Реализует:
- Подключение к SQLite с WAL-режимом
- Создание схемы базы данных
- CRUD-операции для агентов, задач, блокировок
- Логирование событий
"""

import contextlib
import os
import platform
import re
import sqlite3
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import (
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
)

# Имя переменной окружения для токена сессии
SESSION_ENV_VAR = "SWARM_SESSION"

# Имя файла базы данных
DB_FILENAME = "swarm.db"

# Имя файла сессии агента
SESSION_FILENAME = ".swarm_session"

# Директория сессий внутри .swarm/
SESSIONS_DIR = Path(".swarm") / "sessions"

# Регулярное выражение для валидации имени агента (m-9)
AGENT_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")


# SQL-схема базы данных
SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS agents (
    agent_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token  TEXT    UNIQUE NOT NULL,
    cli_type       TEXT    NOT NULL,
    name           TEXT    NOT NULL UNIQUE,
    role           TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'idle',
    current_task_id INTEGER REFERENCES tasks(task_id),
    registered_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pid            INTEGER
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    description  TEXT    NOT NULL,
    priority     INTEGER NOT NULL DEFAULT 3,
    target_cli   TEXT,
    target_name  TEXT,
    target_role  TEXT,
    status       TEXT    NOT NULL DEFAULT 'pending',
    assigned_to  INTEGER REFERENCES agents(agent_id),
    depends_on   INTEGER REFERENCES tasks(task_id),
    summary      TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at   DATETIME,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS file_locks (
    lock_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path  TEXT    UNIQUE NOT NULL,
    locked_by  INTEGER NOT NULL REFERENCES agents(agent_id),
    task_id    INTEGER NOT NULL REFERENCES tasks(task_id),
    locked_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_log (
    log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id   INTEGER REFERENCES tasks(task_id),
    agent_id  INTEGER REFERENCES agents(agent_id),
    event     TEXT    NOT NULL,
    message   TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS launch_sessions (
    session_id              TEXT PRIMARY KEY,
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    working_directory       TEXT NOT NULL,
    approval_mode           TEXT NOT NULL,
    layout_mode             TEXT NOT NULL,
    requested_agent_count   INTEGER NOT NULL,
    status                  TEXT NOT NULL,
    created_by              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS launch_session_agents (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id           TEXT NOT NULL REFERENCES launch_sessions(session_id),
    cli_type             TEXT NOT NULL,
    agent_name           TEXT NOT NULL,
    agent_role           TEXT NOT NULL,
    window_index         INTEGER,
    pane_index           INTEGER,
    launcher_profile     TEXT NOT NULL,
    bootstrap_prompt     TEXT NOT NULL,
    registration_status  TEXT NOT NULL DEFAULT 'planned',
    registered_agent_id  INTEGER REFERENCES agents(agent_id),
    terminal_pid         INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_file_locks_path ON file_locks(file_path);
CREATE INDEX IF NOT EXISTS idx_task_log_task ON task_log(task_id);
CREATE INDEX IF NOT EXISTS idx_agents_session ON agents(session_token);
CREATE INDEX IF NOT EXISTS idx_launch_sessions_status ON launch_sessions(status);
CREATE INDEX IF NOT EXISTS idx_launch_agents_session ON launch_session_agents(session_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_launch_agents_session_name ON launch_session_agents(session_id, agent_name);
"""




def find_db_path(start_dir: Path | None = None) -> Path | None:
    """Ищет файл swarm.db в текущей директории и родительских."""
    current = start_dir or Path.cwd()
    while current != current.parent:
        db_path = current / DB_FILENAME
        if db_path.exists():
            return db_path
        current = current.parent
    db_path = current / DB_FILENAME
    if db_path.exists():
        return db_path
    return None


def get_db_path() -> Path:
    """Возвращает путь к файлу БД или бросает FileNotFoundError."""
    db_path = find_db_path()
    if db_path is None:
        raise FileNotFoundError(f"Файл {DB_FILENAME} не найден. Выполните 'swarm init' для инициализации.")
    return db_path


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Контекстный менеджер для подключения к БД."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path), timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database(target_dir: Path | None = None) -> Path:
    """Инициализирует базу данных SWARM."""
    db_dir = target_dir or Path.cwd()
    db_path = db_dir / DB_FILENAME
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    return db_path


def ensure_terminal_schema() -> None:
    """Гарантирует наличие terminal-таблиц в существующей БД.

    Все таблицы (включая terminal) определены в SCHEMA_SQL с IF NOT EXISTS,
    поэтому повторное выполнение безопасно и не затрагивает существующие данные.
    """
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)


def validate_agent_name(name: str) -> None:
    """Проверяет имя агента (m-9): [a-zA-Z0-9_-]{1,32}."""
    if not AGENT_NAME_RE.match(name):
        raise ValueError(
            f"Недопустимое имя агента: '{name}'. Разрешены: латиница, цифры, дефис, подчёркивание (1-32 символа)."
        )


# ============================================================
# Операции с агентами
# ============================================================


def register_agent(session_token: str, cli_type: str, name: str, role: str, pid: int | None = None) -> Agent:
    """Регистрирует нового агента. m-2: атомарно с логом. m-9: валидация имени."""
    validate_agent_name(name)

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            existing = conn.execute("SELECT agent_id FROM agents WHERE name = ?", (name,)).fetchone()
            if existing is not None:
                conn.execute("ROLLBACK")
                raise sqlite3.IntegrityError(f"Агент с именем '{name}' уже зарегистрирован")

            cursor = conn.execute(
                "INSERT INTO agents (session_token, cli_type, name, role, pid) VALUES (?, ?, ?, ?, ?)",
                (session_token, cli_type, name, role, pid),
            )
            agent_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)",
                (None, agent_id, EventType.AGENT_REGISTERED.value, f"Агент {name} ({cli_type}/{role}) зарегистрирован"),
            )

            conn.execute("COMMIT")

            row = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
            return Agent.from_row(row)

        except Exception:
            with contextlib.suppress(Exception):
                conn.execute("ROLLBACK")
            raise


def get_agent_by_session(session_token: str) -> Agent | None:
    """Получает агента по токену сессии."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM agents WHERE session_token = ?", (session_token,)).fetchone()
        if row:
            return Agent.from_row(row)
        return None


def get_agent_by_name(name: str) -> Agent | None:
    """Получает агента по имени."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
        if row:
            return Agent.from_row(row)
        return None


def get_all_agents() -> list[Agent]:
    """Возвращает список всех зарегистрированных агентов."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM agents ORDER BY agent_id").fetchall()
        return [Agent.from_row(row) for row in rows]


def update_agent_heartbeat(agent_id: int) -> None:
    """Обновляет heartbeat агента."""
    with get_connection() as conn:
        conn.execute("UPDATE agents SET last_heartbeat = CURRENT_TIMESTAMP WHERE agent_id = ?", (agent_id,))


def update_agent_status(agent_id: int, status: AgentStatus, task_id: int | None = None) -> None:
    """Обновляет статус агента."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE agents SET status = ?, current_task_id = ?, last_heartbeat = CURRENT_TIMESTAMP WHERE agent_id = ?",
            (status.value, task_id, agent_id),
        )


def is_process_alive(pid: int | None) -> bool:
    """Проверяет, жив ли процесс с указанным PID.

    На Windows использует tasklist для надёжной проверки,
    т.к. os.kill(pid, 0) не различает живой процесс и переиспользованный PID.
    """
    if pid is None:
        return False
    if platform.system() == "Windows":
        try:
            # Не используем text=True — на Windows вывод может быть в cp866,
            # что вызывает UnicodeDecodeError
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                timeout=5,
            )
            # Проверяем наличие PID в выводе (байтовая строка)
            return str(pid).encode() in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Фоллбэк на os.kill если tasklist недоступен
            pass
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cleanup_dead_agents(timeout_minutes: int = 30, check_pid: bool = True, force_all: bool = False) -> int:
    """Удаляет неактивных агентов. M-1: освобождает задачи/блокировки. m-4: UTC.

    КРИТ-1: при force_all=True освобождает задачи и блокировки перед удалением.
    ВАЖ-6: все операции обёрнуты в BEGIN IMMEDIATE для атомарности.
    """
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            if force_all:
                # КРИТ-1: освобождаем задачи и блокировки перед удалением всех агентов
                conn.execute("UPDATE tasks SET status = 'failed', assigned_to = NULL WHERE status = 'in_progress'")
                conn.execute("DELETE FROM file_locks")
                cursor = conn.execute("DELETE FROM agents")
                conn.execute("COMMIT")
                return cursor.rowcount

            now = datetime.now(UTC).replace(tzinfo=None)
            heartbeat_deadline = now - timedelta(minutes=timeout_minutes)

            rows = conn.execute("SELECT agent_id, last_heartbeat, pid FROM agents").fetchall()
            removable_agent_ids = []

            for row in rows:
                agent_id = row["agent_id"]
                last_heartbeat = row["last_heartbeat"]
                pid = row["pid"]
                heartbeat_dt = datetime.fromisoformat(last_heartbeat) if isinstance(last_heartbeat, str) else last_heartbeat
                heartbeat_stale = heartbeat_dt < heartbeat_deadline
                pid_alive = is_process_alive(pid) if check_pid and pid is not None else None

                if pid_alive is False:
                    removable_agent_ids.append(agent_id)
                    continue
                if heartbeat_stale and (not check_pid or pid is None):
                    removable_agent_ids.append(agent_id)

            for agent_id in removable_agent_ids:
                conn.execute(
                    "UPDATE tasks SET status = 'failed', assigned_to = NULL WHERE assigned_to = ? AND status = 'in_progress'",
                    (agent_id,),
                )
                conn.execute("DELETE FROM file_locks WHERE locked_by = ?", (agent_id,))
                conn.execute(
                    "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)",
                    (None, agent_id, EventType.AGENT_CLEANUP.value, f"Агент #{agent_id} удалён (неактивен)"),
                )
                conn.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))

            conn.execute("COMMIT")
            return len(removable_agent_ids)

        except Exception:
            with contextlib.suppress(Exception):
                conn.execute("ROLLBACK")
            raise


# ============================================================
# Операции с задачами
# ============================================================


def _has_dependency_cycle(conn: sqlite3.Connection, depends_on: int) -> bool:
    """Проверяет цикл в цепочке зависимостей (m-10)."""
    visited: set[int] = set()
    current_id: int | None = depends_on
    while current_id is not None:
        if current_id in visited:
            return True
        visited.add(current_id)
        row = conn.execute("SELECT depends_on FROM tasks WHERE task_id = ?", (current_id,)).fetchone()
        if row is None:
            break
        current_id = row["depends_on"]
    return False


def create_task(
    description: str,
    priority: int = 3,
    target_cli: str | None = None,
    target_name: str | None = None,
    target_role: str | None = None,
    depends_on: int | None = None,
) -> Task:
    """Создаёт новую задачу. m-10: проверка цикличных зависимостей.

    КРИТ-4: BEGIN IMMEDIATE для атомарности проверки зависимостей и вставки.
    """
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            if depends_on is not None and _has_dependency_cycle(conn, depends_on):
                conn.execute("ROLLBACK")
                raise ValueError(f"Обнаружен цикл в зависимостях: задача {depends_on} участвует в циклической цепочке")

            cursor = conn.execute(
                "INSERT INTO tasks (description, priority, target_cli, target_name, target_role, depends_on) VALUES (?, ?, ?, ?, ?, ?)",
                (description, priority, target_cli, target_name, target_role, depends_on),
            )
            task_id = cursor.lastrowid

            conn.execute("COMMIT")

            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            return Task.from_row(row)

        except ValueError:
            # ValueError от проверки цикла — ROLLBACK уже вызван выше
            raise
        except Exception:
            with contextlib.suppress(Exception):
                conn.execute("ROLLBACK")
            raise


def get_task(task_id: int) -> Task | None:
    """Получает задачу по ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row:
            return Task.from_row(row)
        return None


def get_all_tasks(
    status: TaskStatus | None = None,
    assigned_to: int | None = None,
    priority: int | None = None,
) -> list[Task]:
    """Возвращает список задач с опциональной фильтрацией."""
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status.value)
    if assigned_to is not None:
        query += " AND assigned_to = ?"
        params.append(assigned_to)
    if priority is not None:
        query += " AND priority = ?"
        params.append(priority)
    query += " ORDER BY priority ASC, task_id ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [Task.from_row(row) for row in rows]


def assign_task_to_agent(task_id: int, agent_name: str) -> bool:
    """Назначает задачу конкретному агенту (устанавливает target_name)."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return False
            task = Task.from_row(row)
            if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.DONE):
                conn.execute("ROLLBACK")
                return False
            conn.execute("UPDATE tasks SET target_name = ? WHERE task_id = ?", (agent_name, task_id))
            conn.execute("COMMIT")
            return True
        except Exception:
            conn.execute("ROLLBACK")
            raise


def claim_next_task(agent: Agent) -> Task | None:
    """Атомарно захватывает следующую подходящую задачу для агента."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                """
        SELECT task_id FROM tasks
        WHERE status = 'pending'
          AND (depends_on IS NULL OR depends_on IN (SELECT task_id FROM tasks WHERE status = 'done'))
          AND (target_role IS NULL OR target_role = ?)
          AND (target_name IS NULL OR target_name = ?)
          AND (target_cli  IS NULL OR target_cli  = ?)
        ORDER BY priority ASC, task_id ASC LIMIT 1
        """,
                (agent.role, agent.name, agent.cli_type),
            ).fetchone()

            if row is None:
                conn.execute("ROLLBACK")
                return None

            task_id = row["task_id"]

            conn.execute(
                "UPDATE tasks SET status = 'in_progress', assigned_to = ?, started_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                (agent.agent_id, task_id),
            )
            conn.execute(
                "UPDATE agents SET status = 'working', current_task_id = ?, last_heartbeat = CURRENT_TIMESTAMP WHERE agent_id = ?",
                (task_id, agent.agent_id),
            )
            conn.execute(
                "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)",
                (task_id, agent.agent_id, EventType.TASK_STARTED.value, "Задача начата"),
            )

            conn.execute("COMMIT")

            task_row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            return Task.from_row(task_row)

        except Exception:
            conn.execute("ROLLBACK")
            raise


def complete_task(agent: Agent, summary: str) -> bool:
    """Завершает текущую задачу. M-3: перечитывает агента. M-4: проверяет locked_by."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            agent_row = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (agent.agent_id,)).fetchone()
            if agent_row is None:
                conn.execute("ROLLBACK")
                return False

            fresh_agent = Agent.from_row(agent_row)
            task_id = fresh_agent.current_task_id
            if task_id is None:
                conn.execute("ROLLBACK")
                return False

            conn.execute(
                "UPDATE tasks SET status = 'done', summary = ?, completed_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                (summary, task_id),
            )
            conn.execute("DELETE FROM file_locks WHERE task_id = ? AND locked_by = ?", (task_id, fresh_agent.agent_id))
            conn.execute(
                "UPDATE agents SET status = 'idle', current_task_id = NULL, last_heartbeat = CURRENT_TIMESTAMP WHERE agent_id = ?",
                (fresh_agent.agent_id,),
            )
            conn.execute(
                "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)",
                (task_id, fresh_agent.agent_id, EventType.TASK_DONE.value, summary),
            )

            conn.execute("COMMIT")
            return True

        except Exception:
            conn.execute("ROLLBACK")
            raise


def reset_task(task_id: int) -> bool:
    """Сбрасывает задачу в статус pending: снимает привязку к агенту и освобождает блокировки."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            task_row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if task_row is None:
                conn.execute("ROLLBACK")
                return False

            task = Task.from_row(task_row)
            if task.status == TaskStatus.PENDING:
                conn.execute("ROLLBACK")
                return True

            # Освобождаем агента, если задача была назначена
            if task.assigned_to:
                conn.execute(
                    "UPDATE agents SET status = 'idle', current_task_id = NULL, last_heartbeat = CURRENT_TIMESTAMP WHERE agent_id = ? AND current_task_id = ?",
                    (task.assigned_to, task_id),
                )

            # Снимаем блокировки файлов
            conn.execute("DELETE FROM file_locks WHERE task_id = ?", (task_id,))

            # Сбрасываем задачу
            conn.execute(
                "UPDATE tasks SET status = 'pending', assigned_to = NULL, target_name = NULL, summary = NULL, started_at = NULL, completed_at = NULL WHERE task_id = ?",
                (task_id,),
            )

            conn.execute(
                "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)",
                (task_id, task.assigned_to, EventType.TASK_RESET.value, "Задача сброшена в pending"),
            )

            conn.execute("COMMIT")
            return True

        except Exception:
            conn.execute("ROLLBACK")
            raise


def force_close_task(task_id: int, reason: str = "Принудительно закрыта Лидером") -> bool:
    """Принудительно завершает задачу (команда для Лидера)."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            task_row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if task_row is None:
                conn.execute("ROLLBACK")
                return False

            task = Task.from_row(task_row)
            if task.status == TaskStatus.DONE:
                conn.execute("ROLLBACK")
                return True

            conn.execute(
                "UPDATE tasks SET status = 'done', summary = ?, completed_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                (reason, task_id),
            )
            conn.execute("DELETE FROM file_locks WHERE task_id = ?", (task_id,))

            if task.assigned_to:
                conn.execute(
                    "UPDATE agents SET status = 'idle', current_task_id = NULL, last_heartbeat = CURRENT_TIMESTAMP WHERE agent_id = ? AND current_task_id = ?",
                    (task.assigned_to, task_id),
                )

            # КРИТ-5: логируем TASK_FORCE_CLOSED (не TASK_DONE) — принудительное закрытие
            conn.execute(
                "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)",
                (task_id, task.assigned_to, EventType.TASK_FORCE_CLOSED.value, reason),
            )

            conn.execute("COMMIT")
            return True

        except Exception:
            conn.execute("ROLLBACK")
            raise


# ============================================================
# Операции с блокировками файлов
# ============================================================


def try_lock_file(agent_id: int, task_id: int, file_path: str) -> bool:
    """Пытается захватить блокировку. C-1: BEGIN IMMEDIATE для атомарности."""
    normalized_path = str(Path(file_path).as_posix())

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            existing_path_lock = conn.execute(
                "SELECT locked_by FROM file_locks WHERE file_path = ?", (normalized_path,)
            ).fetchone()

            if existing_path_lock is not None:
                conn.execute("ROLLBACK")
                return existing_path_lock["locked_by"] == agent_id

            existing_agent_lock = conn.execute(
                "SELECT file_path FROM file_locks WHERE locked_by = ?", (agent_id,)
            ).fetchone()

            if existing_agent_lock is not None:
                conn.execute("ROLLBACK")
                return False

            conn.execute(
                "INSERT INTO file_locks (file_path, locked_by, task_id) VALUES (?, ?, ?)",
                (normalized_path, agent_id, task_id),
            )
            conn.execute(
                "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)",
                (task_id, agent_id, EventType.FILE_LOCKED.value, f"Заблокирован файл: {file_path}"),
            )

            conn.execute("COMMIT")
            return True

        except sqlite3.IntegrityError:
            conn.execute("ROLLBACK")
            return False
        except Exception:
            conn.execute("ROLLBACK")
            raise


def get_file_lock(file_path: str) -> FileLock | None:
    """Получает информацию о блокировке файла."""
    normalized_path = str(Path(file_path).as_posix())
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM file_locks WHERE file_path = ?", (normalized_path,)).fetchone()
        if row:
            return FileLock.from_row(row)
        return None


def get_all_locks() -> list[FileLock]:
    """Возвращает все активные блокировки."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM file_locks ORDER BY locked_at").fetchall()
        return [FileLock.from_row(row) for row in rows]


def get_agent_lock(agent_id: int) -> FileLock | None:
    """Возвращает активную блокировку агента."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM file_locks WHERE locked_by = ? ORDER BY locked_at LIMIT 1", (agent_id,)
        ).fetchone()
        if row:
            return FileLock.from_row(row)
        return None


def unlock_file(file_path: str, agent_id: int | None = None, force: bool = False) -> bool:
    """Снимает блокировку с файла."""
    normalized_path = str(Path(file_path).as_posix())
    with get_connection() as conn:
        if force:
            cursor = conn.execute("DELETE FROM file_locks WHERE file_path = ?", (normalized_path,))
        else:
            cursor = conn.execute(
                "DELETE FROM file_locks WHERE file_path = ? AND locked_by = ?", (normalized_path, agent_id)
            )
        return cursor.rowcount > 0


def unlock_task_files(task_id: int) -> int:
    """Снимает все блокировки для задачи."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM file_locks WHERE task_id = ?", (task_id,))
        return cursor.rowcount


# ============================================================
# Операции launch sessions (терминальная оркестрация)
# ============================================================


def create_launch_session(
    session_id: str,
    working_directory: str,
    approval_mode: str,
    layout_mode: str,
    requested_agent_count: int,
    created_by: str = "orchestrator",
    status: LaunchSessionStatus = LaunchSessionStatus.PLANNED,
) -> LaunchSession:
    """Создаёт launch-сессию в БД."""
    with get_connection() as conn:
        conn.execute(
            """
      INSERT INTO launch_sessions (
        session_id, working_directory, approval_mode, layout_mode,
        requested_agent_count, status, created_by
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
      """,
            (
                session_id,
                working_directory,
                approval_mode,
                layout_mode,
                requested_agent_count,
                status.value,
                created_by,
            ),
        )
        row = conn.execute("SELECT * FROM launch_sessions WHERE session_id = ?", (session_id,)).fetchone()
        return LaunchSession.from_row(row)


def get_launch_session(session_id: str) -> LaunchSession | None:
    """Возвращает launch-сессию по ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM launch_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row:
            return LaunchSession.from_row(row)
        return None


def get_launch_sessions(status: LaunchSessionStatus | None = None) -> list[LaunchSession]:
    """Возвращает список launch-сессий с опциональным фильтром по статусу."""
    query = "SELECT * FROM launch_sessions"
    params: list[str] = []
    if status is not None:
        query += " WHERE status = ?"
        params.append(status.value)
    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [LaunchSession.from_row(row) for row in rows]


def update_launch_session_status(session_id: str, status: LaunchSessionStatus) -> bool:
    """Обновляет статус launch-сессии."""
    with get_connection() as conn:
        cursor = conn.execute("UPDATE launch_sessions SET status = ? WHERE session_id = ?", (status.value, session_id))
        return cursor.rowcount > 0


def add_launch_session_agent(
    session_id: str,
    cli_type: str,
    agent_name: str,
    agent_role: str,
    window_index: int | None,
    pane_index: int | None,
    launcher_profile: str,
    bootstrap_prompt: str,
    registration_status: LaunchRegistrationStatus = LaunchRegistrationStatus.PLANNED,
) -> LaunchSessionAgent:
    """Добавляет агента в launch-сессию."""
    validate_agent_name(agent_name)

    with get_connection() as conn:
        cursor = conn.execute(
            """
      INSERT INTO launch_session_agents (
        session_id, cli_type, agent_name, agent_role, window_index, pane_index,
        launcher_profile, bootstrap_prompt, registration_status
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
            (
                session_id,
                cli_type,
                agent_name,
                agent_role,
                window_index,
                pane_index,
                launcher_profile,
                bootstrap_prompt,
                registration_status.value,
            ),
        )
        row = conn.execute("SELECT * FROM launch_session_agents WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return LaunchSessionAgent.from_row(row)


def get_launch_session_agents(session_id: str) -> list[LaunchSessionAgent]:
    """Возвращает агентов launch-сессии."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM launch_session_agents WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [LaunchSessionAgent.from_row(row) for row in rows]


def update_launch_agent_status(
    session_id: str,
    agent_name: str,
    registration_status: LaunchRegistrationStatus,
    terminal_pid: int | None = None,
    registered_agent_id: int | None = None,
) -> bool:
    """Обновляет статус агента в launch-сессии."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
      UPDATE launch_session_agents
      SET registration_status = ?,
          terminal_pid = COALESCE(?, terminal_pid),
          registered_agent_id = COALESCE(?, registered_agent_id)
      WHERE session_id = ? AND agent_name = ?
      """,
            (
                registration_status.value,
                terminal_pid,
                registered_agent_id,
                session_id,
                agent_name,
            ),
        )
        return cursor.rowcount > 0


def get_active_launch_agent_names() -> set[str]:
    """Возвращает имена агентов из незавершённых launch-сессий."""
    terminal_statuses = (
        LaunchSessionStatus.STOPPED.value,
        LaunchSessionStatus.FAILED.value,
        LaunchSessionStatus.REGISTERED.value,
    )
    with get_connection() as conn:
        rows = conn.execute(
            """
      SELECT lsa.agent_name
      FROM launch_session_agents lsa
      JOIN launch_sessions ls ON ls.session_id = lsa.session_id
      WHERE ls.status NOT IN (?, ?, ?)
      """,
            terminal_statuses,
        ).fetchall()
        return {row["agent_name"] for row in rows}


def reconcile_launch_session(session_id: str) -> tuple[LaunchSession | None, list[LaunchSessionAgent]]:
    """Сверяет launch-сессию с реально зарегистрированными агентами."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            session_row = conn.execute("SELECT * FROM launch_sessions WHERE session_id = ?", (session_id,)).fetchone()
            if session_row is None:
                conn.execute("ROLLBACK")
                return None, []

            agents_rows = conn.execute(
                "SELECT * FROM launch_session_agents WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()

            registered_count = 0
            failed_count = 0

            for row in agents_rows:
                name = row["agent_name"]
                live_agent = conn.execute("SELECT agent_id FROM agents WHERE name = ?", (name,)).fetchone()
                if live_agent is not None:
                    registered_count += 1
                    conn.execute(
                        """
            UPDATE launch_session_agents
            SET registration_status = ?, registered_agent_id = ?
            WHERE id = ?
            """,
                        (LaunchRegistrationStatus.REGISTERED.value, live_agent["agent_id"], row["id"]),
                    )
                elif row["registration_status"] == LaunchRegistrationStatus.FAILED.value:
                    failed_count += 1

            total = len(agents_rows)
            if total == 0 or failed_count == total:
                new_status = LaunchSessionStatus.FAILED
            elif registered_count == total:
                new_status = LaunchSessionStatus.REGISTERED
            elif registered_count > 0 or failed_count > 0:
                new_status = LaunchSessionStatus.PARTIALLY_REGISTERED
            else:
                new_status = LaunchSessionStatus.LAUNCHED

            conn.execute("UPDATE launch_sessions SET status = ? WHERE session_id = ?", (new_status.value, session_id))
            conn.execute("COMMIT")

        except Exception:
            with contextlib.suppress(Exception):
                conn.execute("ROLLBACK")
            raise

    session = get_launch_session(session_id)
    agents = get_launch_session_agents(session_id)
    return session, agents


# ============================================================
# Логирование событий
# ============================================================


def log_event(
    event: EventType,
    task_id: int | None = None,
    agent_id: int | None = None,
    message: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Записывает событие в лог."""
    sql = "INSERT INTO task_log (task_id, agent_id, event, message) VALUES (?, ?, ?, ?)"
    params = (task_id, agent_id, event.value, message)
    if conn is not None:
        conn.execute(sql, params)
    else:
        with get_connection() as new_conn:
            new_conn.execute(sql, params)


def get_recent_events(
    limit: int = 20,
    task_id: int | None = None,
    agent_id: int | None = None,
    since_hours: float | None = None,
) -> list[TaskLogEntry]:
    """Возвращает последние события. m-5: фильтрация в SQL."""
    query = "SELECT * FROM task_log WHERE 1=1"
    params: list = []
    if task_id is not None:
        query += " AND task_id = ?"
        params.append(task_id)
    if agent_id is not None:
        query += " AND agent_id = ?"
        params.append(agent_id)
    if since_hours is not None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=since_hours)
        query += " AND timestamp >= ?"
        params.append(cutoff.strftime("%Y-%m-%d %H:%M:%S"))
    query += " ORDER BY timestamp DESC, log_id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [TaskLogEntry.from_row(row) for row in rows]


# ============================================================
# Утилиты сессии агента
# ============================================================


def _detect_shell_command(agent_name: str) -> str:
    """Определяет команду установки env-переменной для текущей оболочки (m-7)."""
    shell = os.environ.get("SHELL", "")
    if platform.system() == "Windows" and not shell:
        return f'$env:SWARM_AGENT = "{agent_name}"'
    if "fish" in shell:
        return f'set -x SWARM_AGENT "{agent_name}"'
    return f'export SWARM_AGENT="{agent_name}"'


def save_session_token(token: str, agent_name: str, directory: Path | None = None) -> tuple[Path, str]:
    """Сохраняет токен сессии. C-5: токен не в env. M-8: права 0600."""
    os.environ["SWARM_AGENT"] = agent_name

    target_dir = directory or Path.cwd()
    sessions_dir = target_dir / SESSIONS_DIR
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_path = sessions_dir / f".swarm_session_{agent_name}"
    # ВАЖ-4: явное encoding для корректной работы на Windows (cp1251 по умолчанию)
    session_path.write_text(token, encoding="utf-8")
    with contextlib.suppress(OSError):
        os.chmod(session_path, 0o600)

    env_command = _detect_shell_command(agent_name)
    return session_path, env_command


def load_session_token(directory: Path | None = None) -> str | None:
    """Загружает токен сессии из файла или env."""
    env_token = os.environ.get(SESSION_ENV_VAR)
    if env_token:
        return env_token.strip()

    agent_name = os.environ.get("SWARM_AGENT")
    if not agent_name:
        target_dir = directory or Path.cwd()
        # Проверяем .swarm/sessions/ (новый путь)
        new_session_path = target_dir / SESSIONS_DIR / SESSION_FILENAME
        if new_session_path.exists():
            # ВАЖ-4: явное encoding для корректной работы на Windows
            return new_session_path.read_text(encoding="utf-8").strip()
        # Fallback на корень (legacy)
        old_session_path = target_dir / SESSION_FILENAME
        if old_session_path.exists():
            return old_session_path.read_text(encoding="utf-8").strip()
        return None

    target_dir = directory or Path.cwd()
    # Проверяем .swarm/sessions/ (новый путь)
    session_path = target_dir / SESSIONS_DIR / f".swarm_session_{agent_name}"
    if session_path.exists():
        return session_path.read_text(encoding="utf-8").strip()
    # Fallback на корень (legacy)
    legacy_path = target_dir / f".swarm_session_{agent_name}"
    if legacy_path.exists():
        return legacy_path.read_text(encoding="utf-8").strip()
    return None


def get_current_agent() -> Agent | None:
    """Получает текущего агента по сохранённой сессии."""
    token = load_session_token()
    if token:
        return get_agent_by_session(token)
    return None

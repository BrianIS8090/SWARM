"""
Модуль работы с базой данных SWARM.

Реализует:
- Подключение к SQLite с WAL-режимом
- Создание схемы базы данных
- CRUD-операции для агентов, задач, блокировок
- Логирование событий
"""

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from .models import Agent, AgentStatus, EventType, FileLock, Task, TaskLogEntry, TaskStatus

# Имя переменной окружения для токена сессии
SESSION_ENV_VAR = "SWARM_SESSION"

# Имя файла базы данных
DB_FILENAME = "swarm.db"

# Имя файла сессии агента
SESSION_FILENAME = ".swarm_session"


# SQL-схема базы данных
SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS agents (
    agent_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token  TEXT    UNIQUE NOT NULL,
    cli_type       TEXT    NOT NULL,
    name           TEXT    NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_file_locks_path ON file_locks(file_path);
CREATE INDEX IF NOT EXISTS idx_task_log_task ON task_log(task_id);
CREATE INDEX IF NOT EXISTS idx_agents_session ON agents(session_token);
"""


def find_db_path(start_dir: Path | None = None) -> Path | None:
    """
    Ищет файл swarm.db в текущей директории и родительских.
    
    Args:
        start_dir: Начальная директория для поиска (по умолчанию текущая)
        
    Returns:
        Путь к файлу БД или None, если не найден
    """
    current = start_dir or Path.cwd()

    while current != current.parent:
        db_path = current / DB_FILENAME
        if db_path.exists():
            return db_path
        current = current.parent

    # Проверяем корень
    db_path = current / DB_FILENAME
    if db_path.exists():
        return db_path

    return None


def get_db_path() -> Path:
    """
    Возвращает путь к файлу БД.
    
    Raises:
        FileNotFoundError: Если swarm.db не найден
    """
    db_path = find_db_path()
    if db_path is None:
        raise FileNotFoundError(
            f"Файл {DB_FILENAME} не найден. Выполните 'swarm init' для инициализации."
        )
    return db_path


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Контекстный менеджер для подключения к БД.
    
    Args:
        db_path: Путь к файлу БД (по умолчанию ищется автоматически)
        
    Yields:
        Соединение с БД
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database(target_dir: Path | None = None) -> Path:
    """
    Инициализирует базу данных SWARM.
    
    Создаёт файл swarm.db с полной схемой и включает WAL-режим.
    
    Args:
        target_dir: Директория для создания БД (по умолчанию текущая)
        
    Returns:
        Путь к созданному файлу БД
    """
    db_dir = target_dir or Path.cwd()
    db_path = db_dir / DB_FILENAME

    # Создаём директорию, если не существует
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        # Выполняем схему (включая WAL)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

    return db_path


# ============================================================
# Операции с агентами
# ============================================================

def register_agent(
    session_token: str,
    cli_type: str,
    name: str,
    role: str,
    pid: int | None = None,
) -> Agent:
    """
    Регистрирует нового агента в системе.
    
    Args:
        session_token: UUID сессии
        cli_type: Тип CLI (claude, codex, gemini)
        name: Имя агента
        role: Роль агента (architect, developer, tester, devops)
        pid: PID процесса (опционально)
        
    Returns:
        Созданный агент
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO agents (session_token, cli_type, name, role, pid)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_token, cli_type, name, role, pid),
        )
        conn.commit()
        agent_id = cursor.lastrowid

        # Логируем событие
        log_event(
            conn=conn,
            event=EventType.AGENT_REGISTERED,
            agent_id=agent_id,
            message=f"Агент {name} ({cli_type}/{role}) зарегистрирован",
        )

        # Получаем созданного агента
        row = conn.execute(
            "SELECT * FROM agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()

        return Agent.from_row(tuple(row))


def get_agent_by_session(session_token: str) -> Agent | None:
    """
    Получает агента по токену сессии.
    
    Args:
        session_token: UUID сессии
        
    Returns:
        Агент или None
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM agents WHERE session_token = ?",
            (session_token,),
        ).fetchone()

        if row:
            return Agent.from_row(tuple(row))
        return None


def get_agent_by_name(name: str) -> Agent | None:
    """
    Получает агента по имени.
    
    Args:
        name: Имя агента
        
    Returns:
        Агент или None
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM agents WHERE name = ?",
            (name,),
        ).fetchone()

        if row:
            return Agent.from_row(tuple(row))
        return None


def get_all_agents() -> list[Agent]:
    """
    Возвращает список всех зарегистрированных агентов.
    """
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM agents ORDER BY agent_id").fetchall()
        return [Agent.from_row(tuple(row)) for row in rows]


def update_agent_heartbeat(agent_id: int) -> None:
    """Обновляет heartbeat агента."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE agents SET last_heartbeat = CURRENT_TIMESTAMP WHERE agent_id = ?",
            (agent_id,),
        )
        conn.commit()


def update_agent_status(agent_id: int, status: AgentStatus, task_id: int | None = None) -> None:
    """
    Обновляет статус агента.
    
    Args:
        agent_id: ID агента
        status: Новый статус
        task_id: ID текущей задачи (опционально)
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE agents 
            SET status = ?, current_task_id = ?, last_heartbeat = CURRENT_TIMESTAMP 
            WHERE agent_id = ?
            """,
            (status.value, task_id, agent_id),
        )
        conn.commit()


def _is_process_alive(pid: int | None) -> bool:
    """
    Проверяет, жив ли процесс с указанным PID.
    
    Args:
        pid: ID процесса
        
    Returns:
        True если процесс жив, False если мёртв или pid=None
    """
    if pid is None:
        return False
    try:
        # На Windows и Unix os.kill(pid, 0) проверяет существование процесса
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cleanup_dead_agents(timeout_minutes: int = 30, check_pid: bool = True, force_all: bool = False) -> int:
    """
    Удаляет неактивных агентов.
    
    Args:
        timeout_minutes: Таймаут heartbeat в минутах
        check_pid: Проверять ли живость процесса по PID
        force_all: Удалить ВСЕХ агентов (игнорирует остальные параметры)
        
    Returns:
        Количество удалённых агентов
    """
    with get_connection() as conn:
        if force_all:
            # Удаляем всех агентов
            cursor = conn.execute("DELETE FROM agents")
            conn.commit()
            return cursor.rowcount
        
        removed = 0
        
        # Сначала удаляем по таймауту heartbeat
        cursor = conn.execute(
            """
            DELETE FROM agents 
            WHERE datetime(last_heartbeat, '+' || ? || ' minutes') < datetime('now')
            """,
            (timeout_minutes,),
        )
        conn.commit()
        removed += cursor.rowcount
        
        # Затем проверяем PID оставшихся агентов
        if check_pid:
            cursor = conn.execute("SELECT agent_id, pid FROM agents WHERE pid IS NOT NULL")
            dead_agent_ids = []
            
            for row in cursor.fetchall():
                agent_id, pid = row
                if not _is_process_alive(pid):
                    dead_agent_ids.append(agent_id)
            
            # Удаляем агентов с мёртвыми процессами
            for agent_id in dead_agent_ids:
                conn.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
            
            conn.commit()
            removed += len(dead_agent_ids)
        
        return removed


# ============================================================
# Операции с задачами
# ============================================================

def create_task(
    description: str,
    priority: int = 3,
    target_cli: str | None = None,
    target_name: str | None = None,
    target_role: str | None = None,
    depends_on: int | None = None,
) -> Task:
    """
    Создаёт новую задачу в очереди.
    
    Args:
        description: Описание задачи
        priority: Приоритет (1-5, где 1 — наивысший)
        target_cli: Фильтр по типу CLI
        target_name: Фильтр по имени агента
        target_role: Фильтр по роли
        depends_on: ID задачи-зависимости
        
    Returns:
        Созданная задача
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (description, priority, target_cli, target_name, target_role, depends_on)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (description, priority, target_cli, target_name, target_role, depends_on),
        )
        conn.commit()
        task_id = cursor.lastrowid

        # Получаем созданную задачу
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()

        return Task.from_row(tuple(row))


def get_task(task_id: int) -> Task | None:
    """Получает задачу по ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()

        if row:
            return Task.from_row(tuple(row))
        return None


def get_all_tasks(
    status: TaskStatus | None = None,
    assigned_to: int | None = None,
    priority: int | None = None,
) -> list[Task]:
    """
    Возвращает список задач с опциональной фильтрацией.
    
    Args:
        status: Фильтр по статусу
        assigned_to: Фильтр по агенту
        priority: Фильтр по приоритету
    """
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

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
        return [Task.from_row(tuple(row)) for row in rows]


def assign_task_to_agent(task_id: int, agent_name: str) -> bool:
    """
    Назначает задачу конкретному агенту (устанавливает target_name).
    
    Args:
        task_id: ID задачи
        agent_name: Имя агента
        
    Returns:
        True если успешно, False если задача не найдена или уже выполняется
    """
    with get_connection() as conn:
        # Проверяем задачу
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        
        if row is None:
            return False
        
        task = Task.from_row(tuple(row))
        
        # Нельзя назначить задачу, которая уже выполняется или завершена
        if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.DONE):
            return False
        
        # Обновляем target_name
        conn.execute(
            "UPDATE tasks SET target_name = ? WHERE task_id = ?",
            (agent_name, task_id),
        )
        conn.commit()
        return True


def claim_next_task(agent: Agent) -> Task | None:
    """
    Атомарно захватывает следующую подходящую задачу для агента.
    
    Применяет цепочку фильтров:
    1. Проверка зависимостей
    2. Фильтр по роли
    3. Фильтр по имени
    4. Фильтр по типу CLI
    5. Сортировка по приоритету
    
    Args:
        agent: Агент, запрашивающий задачу
        
    Returns:
        Захваченная задача или None
    """
    with get_connection() as conn:
        # Начинаем немедленную транзакцию для атомарности
        conn.execute("BEGIN IMMEDIATE")

        try:
            # Ищем подходящую задачу
            row = conn.execute(
                """
                SELECT task_id FROM tasks
                WHERE status = 'pending'
                  AND (depends_on IS NULL
                       OR depends_on IN (SELECT task_id FROM tasks WHERE status = 'done'))
                  AND (target_role IS NULL OR target_role = ?)
                  AND (target_name IS NULL OR target_name = ?)
                  AND (target_cli  IS NULL OR target_cli  = ?)
                ORDER BY priority ASC, task_id ASC
                LIMIT 1
                """,
                (agent.role, agent.name, agent.cli_type),
            ).fetchone()

            if row is None:
                conn.execute("ROLLBACK")
                return None

            task_id = row[0]

            # Захватываем задачу
            conn.execute(
                """
                UPDATE tasks 
                SET status = 'in_progress', 
                    assigned_to = ?,
                    started_at = CURRENT_TIMESTAMP 
                WHERE task_id = ?
                """,
                (agent.agent_id, task_id),
            )

            # Обновляем статус агента
            conn.execute(
                """
                UPDATE agents 
                SET status = 'working', 
                    current_task_id = ?,
                    last_heartbeat = CURRENT_TIMESTAMP 
                WHERE agent_id = ?
                """,
                (task_id, agent.agent_id),
            )

            # Логируем
            conn.execute(
                """
                INSERT INTO task_log (task_id, agent_id, event, message)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, agent.agent_id, EventType.TASK_STARTED.value, "Задача начата"),
            )

            conn.execute("COMMIT")

            # Получаем задачу
            task_row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()

            return Task.from_row(tuple(task_row))

        except Exception:
            conn.execute("ROLLBACK")
            raise


def complete_task(agent: Agent, summary: str) -> bool:
    """
    Завершает текущую задачу агента.
    
    Атомарно:
    - Обновляет статус задачи на 'done'
    - Записывает резюме
    - Снимает все блокировки файлов
    - Устанавливает статус агента в 'idle'
    
    Args:
        agent: Агент, завершающий задачу
        summary: Резюме выполненной работы
        
    Returns:
        True если успешно, False если нет активной задачи
    """
    if agent.current_task_id is None:
        return False

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")

        try:
            task_id = agent.current_task_id

            # Обновляем задачу
            conn.execute(
                """
                UPDATE tasks 
                SET status = 'done', 
                    summary = ?,
                    completed_at = CURRENT_TIMESTAMP 
                WHERE task_id = ?
                """,
                (summary, task_id),
            )

            # Снимаем блокировки
            conn.execute(
                "DELETE FROM file_locks WHERE task_id = ?",
                (task_id,),
            )

            # Обновляем агента
            conn.execute(
                """
                UPDATE agents 
                SET status = 'idle', 
                    current_task_id = NULL,
                    last_heartbeat = CURRENT_TIMESTAMP 
                WHERE agent_id = ?
                """,
                (agent.agent_id,),
            )

            # Логируем
            conn.execute(
                """
                INSERT INTO task_log (task_id, agent_id, event, message)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, agent.agent_id, EventType.TASK_DONE.value, summary),
            )

            conn.execute("COMMIT")
            return True

        except Exception:
            conn.execute("ROLLBACK")
            raise


def force_close_task(task_id: int, reason: str = "Принудительно закрыта Лидером") -> bool:
    """
    Принудительно завершает задачу (команда для Лидера).
    
    Атомарно:
    - Обновляет статус задачи на 'done'
    - Записывает причину закрытия
    - Снимает все блокировки файлов
    - Освобождает агента (если был назначен)
    
    Args:
        task_id: ID задачи
        reason: Причина закрытия
        
    Returns:
        True если успешно, False если задача не найдена
    """
    with get_connection() as conn:
        # Проверяем существование задачи
        task_row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        
        if task_row is None:
            return False
        
        task = Task.from_row(tuple(task_row))
        
        # Если задача уже завершена — ничего не делаем
        if task.status == TaskStatus.DONE:
            return True
        
        conn.execute("BEGIN IMMEDIATE")
        
        try:
            # Обновляем задачу
            conn.execute(
                """
                UPDATE tasks 
                SET status = 'done', 
                    summary = ?,
                    completed_at = CURRENT_TIMESTAMP 
                WHERE task_id = ?
                """,
                (reason, task_id),
            )
            
            # Снимаем блокировки
            conn.execute(
                "DELETE FROM file_locks WHERE task_id = ?",
                (task_id,),
            )
            
            # Освобождаем агента (если был назначен)
            if task.assigned_to:
                conn.execute(
                    """
                    UPDATE agents 
                    SET status = 'idle', 
                        current_task_id = NULL,
                        last_heartbeat = CURRENT_TIMESTAMP 
                    WHERE agent_id = ? AND current_task_id = ?
                    """,
                    (task.assigned_to, task_id),
                )
            
            # Логируем
            conn.execute(
                """
                INSERT INTO task_log (task_id, agent_id, event, message)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, task.assigned_to, EventType.TASK_DONE.value, reason),
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
    """
    Пытается захватить блокировку на файл.
    
    Args:
        agent_id: ID агента
        task_id: ID задачи
        file_path: Путь к файлу
        
    Returns:
        True если блокировка получена, False если файл занят
    """
    # Нормализуем путь
    normalized_path = str(Path(file_path).as_posix())

    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO file_locks (file_path, locked_by, task_id)
                VALUES (?, ?, ?)
                """,
                (normalized_path, agent_id, task_id),
            )
            conn.commit()

            # Логируем
            log_event(
                conn=conn,
                event=EventType.FILE_LOCKED,
                agent_id=agent_id,
                task_id=task_id,
                message=f"Заблокирован файл: {file_path}",
            )

            return True
        except sqlite3.IntegrityError:
            # Файл уже заблокирован
            return False


def get_file_lock(file_path: str) -> FileLock | None:
    """Получает информацию о блокировке файла."""
    normalized_path = str(Path(file_path).as_posix())

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM file_locks WHERE file_path = ?",
            (normalized_path,),
        ).fetchone()

        if row:
            return FileLock.from_row(tuple(row))
        return None


def get_all_locks() -> list[FileLock]:
    """Возвращает все активные блокировки."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM file_locks ORDER BY locked_at").fetchall()
        return [FileLock.from_row(tuple(row)) for row in rows]


def unlock_file(file_path: str, agent_id: int | None = None, force: bool = False) -> bool:
    """
    Снимает блокировку с файла.
    
    Args:
        file_path: Путь к файлу
        agent_id: ID агента (если не force)
        force: Принудительное снятие (для Лидера)
        
    Returns:
        True если блокировка снята
    """
    normalized_path = str(Path(file_path).as_posix())

    with get_connection() as conn:
        if force:
            cursor = conn.execute(
                "DELETE FROM file_locks WHERE file_path = ?",
                (normalized_path,),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM file_locks WHERE file_path = ? AND locked_by = ?",
                (normalized_path, agent_id),
            )

        conn.commit()
        return cursor.rowcount > 0


def unlock_task_files(task_id: int) -> int:
    """
    Снимает все блокировки для задачи.
    
    Returns:
        Количество снятых блокировок
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM file_locks WHERE task_id = ?",
            (task_id,),
        )
        conn.commit()
        return cursor.rowcount


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
    """
    Записывает событие в лог.
    
    Args:
        event: Тип события
        task_id: ID задачи (опционально)
        agent_id: ID агента (опционально)
        message: Сообщение (опционально)
        conn: Существующее соединение (опционально)
    """
    if conn is not None:
        conn.execute(
            """
            INSERT INTO task_log (task_id, agent_id, event, message)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, agent_id, event.value, message),
        )
        conn.commit()
    else:
        with get_connection() as new_conn:
            new_conn.execute(
                """
                INSERT INTO task_log (task_id, agent_id, event, message)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, agent_id, event.value, message),
            )
            new_conn.commit()


def get_recent_events(limit: int = 20) -> list[TaskLogEntry]:
    """
    Возвращает последние события из лога.
    
    Args:
        limit: Максимальное количество событий
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM task_log 
            ORDER BY timestamp DESC, log_id DESC 
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [TaskLogEntry.from_row(tuple(row)) for row in rows]


# ============================================================
# Утилиты сессии агента
# ============================================================

def save_session_token(token: str, agent_name: str, directory: Path | None = None) -> tuple[Path, str]:
    """
    Сохраняет токен сессии в файл .swarm_session_<имя_агента>.
    
    Каждый агент имеет свой файл сессии, что позволяет запускать
    несколько агентов одного типа в разных терминалах.
    
    Args:
        token: UUID сессии
        agent_name: Имя агента (для уникального имени файла)
        directory: Директория (по умолчанию текущая)
        
    Returns:
        Кортеж (путь к файлу сессии, команда для установки переменной)
    """
    # Сохраняем имя агента в переменную окружения текущего процесса
    os.environ["SWARM_AGENT"] = agent_name
    os.environ[SESSION_ENV_VAR] = token
    
    # Сохраняем в уникальный файл для этого агента
    target_dir = directory or Path.cwd()
    session_path = target_dir / f".swarm_session_{agent_name}"
    session_path.write_text(token)
    
    # Возвращаем команду для установки в терминале
    env_command = f'$env:SWARM_AGENT = "{agent_name}"'
    
    return session_path, env_command


def load_session_token(directory: Path | None = None) -> str | None:
    """
    Загружает токен сессии из файла .swarm_session_<имя_агента>.
    
    Использует переменную SWARM_AGENT для определения имени агента,
    затем читает соответствующий файл сессии.
    
    Args:
        directory: Директория для поиска файла (по умолчанию текущая)
        
    Returns:
        Токен сессии или None
    """
    # Сначала проверяем прямую переменную с токеном
    env_token = os.environ.get(SESSION_ENV_VAR)
    if env_token:
        return env_token.strip()
    
    # Получаем имя агента из переменной окружения
    agent_name = os.environ.get("SWARM_AGENT")
    if not agent_name:
        # Fallback на старый файл для обратной совместимости
        target_dir = directory or Path.cwd()
        old_session_path = target_dir / SESSION_FILENAME
        if old_session_path.exists():
            return old_session_path.read_text().strip()
        return None
    
    # Читаем файл сессии для этого агента
    target_dir = directory or Path.cwd()
    session_path = target_dir / f".swarm_session_{agent_name}"

    if session_path.exists():
        return session_path.read_text().strip()
    return None


def get_current_agent() -> Agent | None:
    """
    Получает текущего агента по сохранённой сессии.
    
    Returns:
        Агент или None если не зарегистрирован
    """
    token = load_session_token()
    if token:
        return get_agent_by_session(token)
    return None

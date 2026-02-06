"""
TUI-монитор SWARM на базе Textual.

Полноценный интерфейс со скроллингом и обновлением в реальном времени.
"""

from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static
from textual.timer import Timer

from ..db import find_db_path, get_all_agents, get_all_tasks, get_all_locks, get_recent_events
from ..models import AgentStatus, TaskStatus


class AgentsPanel(Static):
    """Панель агентов."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="agents-table")

    def on_mount(self) -> None:
        table = self.query_one("#agents-table", DataTable)
        table.add_columns("ID", "Имя", "CLI", "Роль", "Статус", "Задача", "Heartbeat")
        self.refresh_data()

    def refresh_data(self) -> None:
        """Обновляет данные агентов."""
        table = self.query_one("#agents-table", DataTable)
        table.clear()

        agents = get_all_agents()
        now = datetime.now()

        for agent in agents:
            # Время с последнего heartbeat
            if agent.last_heartbeat:
                delta = now - agent.last_heartbeat
                secs = int(delta.total_seconds())
                if secs < 60:
                    hb_str = f"{secs}с"
                elif secs < 3600:
                    hb_str = f"{secs // 60}м"
                else:
                    hb_str = f"{secs // 3600}ч"
            else:
                hb_str = "-"

            # Статус
            status_icons = {
                AgentStatus.IDLE: "⚪ idle",
                AgentStatus.WORKING: "🟢 working",
                AgentStatus.WAITING: "🟡 waiting",
            }
            status_str = status_icons.get(agent.status, agent.status.value)

            # Задача
            task_str = f"#{agent.current_task_id}" if agent.current_task_id else "-"

            table.add_row(
                str(agent.agent_id),
                agent.name,
                agent.cli_type,
                agent.role or "-",
                status_str,
                task_str,
                hb_str,
            )


class TasksPanel(Static):
    """Панель задач со скроллингом."""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(DataTable(id="tasks-table"), id="tasks-scroll")

    def on_mount(self) -> None:
        table = self.query_one("#tasks-table", DataTable)
        table.add_columns("ID", "P", "Статус", "Роль", "После", "Назначен", "Работает", "Описание")
        self.refresh_data()

    def refresh_data(self) -> None:
        """Обновляет данные задач."""
        table = self.query_one("#tasks-table", DataTable)
        table.clear()

        tasks = get_all_tasks()
        agents = {a.agent_id: a for a in get_all_agents()}

        # Фильтруем завершённые
        tasks = [t for t in tasks if t.status != TaskStatus.DONE]

        status_icons = {
            TaskStatus.PENDING: "⏳ pending",
            TaskStatus.IN_PROGRESS: "🔄 in_prog",
            TaskStatus.DONE: "✓ done",
            TaskStatus.BLOCKED: "🚫 blocked",
        }

        for task in tasks:
            status_str = status_icons.get(task.status, task.status.value)
            assigned_str = task.target_name if task.target_name else "-"
            role_str = task.target_role if task.target_role else "-"
            depends_str = f"#{task.depends_on}" if task.depends_on else "-"

            # Имя агента
            if task.assigned_to:
                agent = agents.get(task.assigned_to)
                working_str = agent.name if agent else f"#{task.assigned_to}"
            else:
                working_str = "-"

            # Описание (до 40 символов)
            desc = task.description
            if len(desc) > 40:
                desc = desc[:37] + "..."

            table.add_row(
                f"#{task.task_id}",
                str(task.priority),
                status_str,
                role_str,
                depends_str,
                assigned_str,
                working_str,
                desc,
            )


class LocksPanel(Static):
    """Панель блокировок."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="locks-table")

    def on_mount(self) -> None:
        table = self.query_one("#locks-table", DataTable)
        table.add_columns("Файл", "Агент", "Время")
        self.refresh_data()

    def refresh_data(self) -> None:
        """Обновляет данные блокировок."""
        table = self.query_one("#locks-table", DataTable)
        table.clear()

        locks = get_all_locks()
        agents = {a.agent_id: a for a in get_all_agents()}
        now = datetime.now()

        for lock in locks:
            # Имя агента
            agent = agents.get(lock.locked_by)
            agent_name = agent.name if agent else f"#{lock.locked_by}"

            # Время блокировки
            if lock.locked_at:
                delta = now - lock.locked_at
                mins = int(delta.total_seconds() / 60)
                if mins < 60:
                    time_str = f"{mins}м"
                else:
                    time_str = f"{mins // 60}ч {mins % 60}м"
            else:
                time_str = "-"

            # Путь
            path = lock.file_path
            if len(path) > 40:
                path = "..." + path[-37:]

            table.add_row(path, agent_name, time_str)


class ActivityPanel(Static):
    """Панель активности со скроллингом."""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(Static(id="activity-log"), id="activity-scroll")

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        """Обновляет лог активности."""
        log = self.query_one("#activity-log", Static)
        events = get_recent_events(limit=50)
        agents = {a.agent_id: a for a in get_all_agents()}

        lines = []
        event_icons = {
            "task_started": "▶",
            "task_done": "✓",
            "file_locked": "🔒",
            "file_unlocked": "🔓",
            "waiting_for_lock": "⏳",
            "error": "✗",
            "agent_registered": "➕",
            "agent_started": "🚀",
        }

        for event in events:
            # Время
            if event.timestamp:
                time_str = event.timestamp.strftime("%H:%M:%S")
            else:
                time_str = "--:--:--"

            # Агент
            agent = agents.get(event.agent_id) if event.agent_id else None
            agent_name = agent.name if agent else "-"

            # Иконка
            icon = event_icons.get(event.event.value, "•")

            # Задача
            task_str = f"#{event.task_id}" if event.task_id else "   "

            # Сообщение
            msg = event.message or event.event.value
            if len(msg) > 40:
                msg = msg[:37] + "..."

            lines.append(f"{time_str} {icon} {task_str} {agent_name:10} {msg}")

        log.update("\n".join(lines) if lines else "Нет событий")


class SwarmTUI(App):
    """Главное приложение SWARM TUI."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
    }

    AgentsPanel {
        border: solid green;
        height: 100%;
    }

    TasksPanel {
        border: solid magenta;
        height: 100%;
    }

    LocksPanel {
        border: solid yellow;
        height: 100%;
    }

    ActivityPanel {
        border: solid cyan;
        height: 100%;
    }

    #tasks-scroll {
        height: 100%;
    }

    #activity-scroll {
        height: 100%;
    }

    DataTable {
        height: auto;
    }

    #activity-log {
        height: auto;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Выход"),
        ("r", "refresh", "Обновить"),
        ("d", "toggle_done", "Показать done"),
    ]

    show_done: reactive[bool] = reactive(False)
    refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield AgentsPanel(id="agents")
        yield TasksPanel(id="tasks")
        yield LocksPanel(id="locks")
        yield ActivityPanel(id="activity")
        yield Footer()

    def on_mount(self) -> None:
        """Запуск автообновления."""
        self.title = "SWARM Monitor"
        self.sub_title = "Ctrl+C или Q для выхода"

        # Автообновление каждые 2 секунды
        self.refresh_timer = self.set_interval(2.0, self.action_refresh)

    def action_refresh(self) -> None:
        """Обновляет все панели."""
        self.query_one("#agents", AgentsPanel).refresh_data()
        self.query_one("#tasks", TasksPanel).refresh_data()
        self.query_one("#locks", LocksPanel).refresh_data()
        self.query_one("#activity", ActivityPanel).refresh_data()

    def action_toggle_done(self) -> None:
        """Переключает показ завершённых задач."""
        self.show_done = not self.show_done
        self.notify(f"Показ done: {'вкл' if self.show_done else 'выкл'}")

    def action_quit(self) -> None:
        """Выход из приложения."""
        self.exit()


def run_tui():
    """Запускает TUI-монитор."""
    if find_db_path() is None:
        from rich.console import Console
        Console().print("[red]✗ SWARM не инициализирован. Выполните 'swarm init' сначала.[/red]")
        return

    app = SwarmTUI()
    app.run()

"""
Команда swarm monitor.

Live-дашборд с 4 панелями:
- Панель агентов
- Панель задач
- Панель блокировок
- Панель активности
"""

import time
from datetime import datetime

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ..db import (
    find_db_path,
    get_all_agents,
    get_all_locks,
    get_all_tasks,
    get_recent_events,
)
from ..models import AgentStatus, TaskStatus

console = Console()


def _check_db():
    """Проверяет наличие БД."""
    if find_db_path() is None:
        console.print("[red]✗ SWARM не инициализирован. Выполните 'swarm init' сначала.[/red]")
        raise typer.Exit(1)


def create_agents_panel() -> Panel:
    """Создаёт панель агентов."""
    agents = get_all_agents()

    if not agents:
        return Panel(
            "[dim]Нет зарегистрированных агентов[/dim]",
            title="[bold cyan]Агенты[/bold cyan]",
            border_style="cyan",
        )

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("ID", style="cyan", width=4)
    table.add_column("CLI", width=7)
    table.add_column("Имя", style="green", width=12)
    table.add_column("Роль", width=10)
    table.add_column("Статус", width=10)
    table.add_column("Задача", width=6)
    table.add_column("HB", width=8)

    status_styles = {
        AgentStatus.IDLE: ("dim", "💤"),
        AgentStatus.WORKING: ("green", "🔄"),
        AgentStatus.WAITING: ("yellow", "⏳"),
        AgentStatus.DONE: ("blue", "✓"),
    }

    now = datetime.now()

    for agent in agents:
        style, icon = status_styles.get(agent.status, ("white", ""))

        # Heartbeat
        if agent.last_heartbeat:
            delta = now - agent.last_heartbeat
            secs = int(delta.total_seconds())
            if secs < 60:
                hb = f"{secs}с"
            elif secs < 3600:
                hb = f"{secs // 60}м"
            else:
                hb = f"{secs // 3600}ч"

            # Подсветка мёртвых
            if secs > 300:
                hb = f"[red]{hb}[/red]"
        else:
            hb = "-"

        task_str = f"#{agent.current_task_id}" if agent.current_task_id else "-"

        table.add_row(
            f"#{agent.agent_id}",
            agent.cli_type,
            agent.name,
            agent.role,
            f"[{style}]{icon} {agent.status.value}[/{style}]",
            task_str,
            hb,
        )

    return Panel(
        table,
        title=f"[bold cyan]Агенты ({len(agents)})[/bold cyan]",
        border_style="cyan",
    )


def create_tasks_panel(show_done: bool = False, full_desc: bool = False) -> Panel:
    """Создаёт панель задач."""
    tasks = get_all_tasks()
    agents = {a.agent_id: a for a in get_all_agents()}

    if not show_done:
        tasks = [t for t in tasks if t.status != TaskStatus.DONE]

    if not tasks:
        return Panel(
            "[dim]Нет активных задач[/dim]",
            title="[bold magenta]Задачи[/bold magenta]",
            border_style="magenta",
        )

    status_styles = {
        TaskStatus.PENDING: ("yellow", "⏳"),
        TaskStatus.IN_PROGRESS: ("green", "🔄"),
        TaskStatus.DONE: ("dim", "✓"),
        TaskStatus.BLOCKED: ("red", "🚫"),
    }

    if full_desc:
        # Режим полного описания — список без таблицы
        lines = []
        for task in tasks[:50]:
            style, icon = status_styles.get(task.status, ("white", ""))
            assigned_str = f"→[cyan]{task.target_name}[/cyan]" if task.target_name else ""
            role_str = f"[yellow]{task.target_role}[/yellow]" if task.target_role else ""
            depends_str = f"[dim]после #{task.depends_on}[/dim]" if task.depends_on else ""
            
            # Имя агента вместо ID
            if task.assigned_to:
                agent = agents.get(task.assigned_to)
                working_name = agent.name if agent else f"#{task.assigned_to}"
                working_str = f"[green][{working_name}][/green]"
            else:
                working_str = ""
            
            lines.append(
                f"[bold cyan]#{task.task_id}[/bold cyan] P{task.priority} "
                f"[{style}]{icon} {task.status.value}[/{style}] {role_str} {depends_str} {assigned_str} {working_str}"
            )
            # Полное описание (до 80 символов)
            desc = task.description
            if len(desc) > 80:
                desc = desc[:77] + "..."
            lines.append(f"  {desc}")
        
        content = "\n".join(lines)
    else:
        # Режим таблицы
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("ID", style="cyan", width=4)
        table.add_column("P", width=2)
        table.add_column("Статус", width=11)
        table.add_column("Роль", width=8)
        table.add_column("После", width=5)
        table.add_column("Назначен", width=8)
        table.add_column("Работает", width=8)
        table.add_column("Описание", width=18, overflow="ellipsis")

        for task in tasks[:50]:
            style, icon = status_styles.get(task.status, ("white", ""))
            assigned_str = task.target_name if task.target_name else "-"
            role_str = task.target_role if task.target_role else "-"
            depends_str = f"#{task.depends_on}" if task.depends_on else "-"
            
            # Имя агента вместо ID
            if task.assigned_to:
                agent = agents.get(task.assigned_to)
                working_str = agent.name if agent else f"#{task.assigned_to}"
            else:
                working_str = "-"
            
            desc = task.description
            if len(desc) > 18:
                desc = desc[:15] + "..."

            table.add_row(
                f"#{task.task_id}",
                str(task.priority),
                f"[{style}]{icon} {task.status.value}[/{style}]",
                role_str,
                depends_str,
                f"[cyan]{assigned_str}[/cyan]",
                f"[green]{working_str}[/green]",
                desc,
            )
        content = table

    total = len(get_all_tasks())
    active = len([t for t in get_all_tasks() if t.status != TaskStatus.DONE])

    return Panel(
        content,
        title=f"[bold magenta]Задачи ({active}/{total})[/bold magenta]",
        border_style="magenta",
    )


def create_locks_panel() -> Panel:
    """Создаёт панель блокировок."""
    locks = get_all_locks()
    agents = {a.agent_id: a for a in get_all_agents()}

    if not locks:
        return Panel(
            "[dim]Нет активных блокировок[/dim]",
            title="[bold yellow]Блокировки[/bold yellow]",
            border_style="yellow",
        )

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Файл", style="white", width=30, overflow="ellipsis")
    table.add_column("Агент", width=12)
    table.add_column("Время", width=8)

    now = datetime.now()

    for lock in locks:
        agent = agents.get(lock.locked_by)
        agent_name = agent.name if agent else f"#{lock.locked_by}"

        # Время блокировки
        if lock.locked_at:
            delta = now - lock.locked_at
            mins = int(delta.total_seconds() / 60)
            if mins < 60:
                time_str = f"{mins}мин"
            else:
                time_str = f"{mins // 60}ч {mins % 60}м"

            # Подсветка долгих блокировок (>30 мин)
            if mins > 30:
                time_str = f"[red]{time_str}[/red]"
        else:
            time_str = "-"

        # Усекаем путь
        path = lock.file_path
        if len(path) > 30:
            path = "..." + path[-27:]

        table.add_row(path, agent_name, time_str)

    return Panel(
        table,
        title=f"[bold yellow]Блокировки ({len(locks)})[/bold yellow]",
        border_style="yellow",
    )


def create_activity_panel() -> Panel:
    """Создаёт панель активности."""
    events = get_recent_events(limit=15)
    agents = {a.agent_id: a for a in get_all_agents()}

    if not events:
        return Panel(
            "[dim]Нет событий[/dim]",
            title="[bold green]Активность[/bold green]",
            border_style="green",
        )

    lines = []

    for event in events:
        # Время
        if event.timestamp:
            time_str = event.timestamp.strftime("%H:%M:%S")
        else:
            time_str = "--:--:--"

        # Агент
        agent = agents.get(event.agent_id) if event.agent_id else None
        agent_name = agent.name if agent else "-"

        # Событие
        event_styles = {
            "task_started": ("green", "▶"),
            "task_done": ("blue", "✓"),
            "file_locked": ("yellow", "🔒"),
            "file_unlocked": ("yellow", "🔓"),
            "waiting_for_lock": ("red", "⏳"),
            "error": ("red", "✗"),
            "agent_registered": ("cyan", "➕"),
            "agent_started": ("green", "🚀"),
        }

        style, icon = event_styles.get(event.event.value, ("white", "•"))

        # Номер задачи
        task_str = f"[magenta]#{event.task_id}[/magenta]" if event.task_id else "   "

        # Сообщение
        msg = event.message or event.event.value
        if len(msg) > 35:
            msg = msg[:32] + "..."

        line = f"[dim]{time_str}[/dim] [{style}]{icon}[/{style}] {task_str} [cyan]{agent_name:8}[/cyan] {msg}"
        lines.append(line)

    return Panel(
        "\n".join(lines),
        title="[bold green]Активность[/bold green]",
        border_style="green",
    )


def create_dashboard(show_done: bool = False, full_desc: bool = False) -> Layout:
    """Создаёт полный дашборд."""
    layout = Layout()

    # Верхняя часть: агенты и задачи
    layout.split_column(
        Layout(name="top", ratio=1),
        Layout(name="bottom", ratio=1),
    )

    layout["top"].split_row(
        Layout(create_agents_panel(), name="agents"),
        Layout(create_tasks_panel(show_done, full_desc), name="tasks"),
    )

    layout["bottom"].split_row(
        Layout(create_locks_panel(), name="locks"),
        Layout(create_activity_panel(), name="activity"),
    )

    return layout


def monitor_command(
    refresh: int = typer.Option(2, "--refresh", "-r", help="Интервал обновления в секундах"),
    full: bool = typer.Option(False, "--full", "-f", help="Показывать полное описание задач"),
):
    """
    Запускает live-дашборд мониторинга.
    
    Управление:
    - Ctrl+C: выход
    
    Опции:
    - --full: показывать полное описание задач
    """
    _check_db()

    show_done = False

    console.print("[dim]Запуск монитора... (Ctrl+C для выхода)[/dim]\n")

    try:
        with Live(
            create_dashboard(show_done, full),
            console=console,
            refresh_per_second=1,
            screen=True,
        ) as live:
            while True:
                time.sleep(refresh)
                live.update(create_dashboard(show_done, full))
    except KeyboardInterrupt:
        console.print("\n[dim]Монитор остановлен[/dim]")

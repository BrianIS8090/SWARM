"""
Команда swarm logs.

Показывает историю событий из task_log.
"""


import typer
from rich.console import Console
from rich.table import Table

from ..db import get_all_agents, get_recent_events
from ..utils import check_db as _check_db

console = Console()


def logs_command(
    limit: int = typer.Option(50, "--limit", "-n", help="Количество записей (по умолчанию 50)"),
    task_id: int | None = typer.Option(None, "--task", "-t", help="Фильтр по ID задачи"),
    agent_name: str | None = typer.Option(None, "--agent", "-a", help="Фильтр по имени агента"),
    since: float | None = typer.Option(None, "--since", "-s", help="Показать события за последние N часов (например: 0.5, 1, 24)"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Следить за новыми событиями"),
):
    """
    Показывает журнал событий системы.
    """
    _check_db()

    # Получаем агентов для маппинга ID -> имя
    agents = {a.agent_id: a for a in get_all_agents()}

    # Если указан фильтр по имени агента, находим его ID
    filter_agent_id = None
    if agent_name:
        for agent in agents.values():
            if agent.name == agent_name:
                filter_agent_id = agent.agent_id
                break
        if filter_agent_id is None:
            console.print(f"[red]✗ Агент '{agent_name}' не найден[/red]")
            raise typer.Exit(1)

    # Фильтрация на уровне SQL — гарантирует корректный LIMIT
    events = get_recent_events(limit=limit, task_id=task_id, agent_id=filter_agent_id, since_hours=since)

    if not events:
        console.print("[yellow]Нет событий[/yellow]")
        return

    # Разворачиваем для хронологического порядка
    events = list(reversed(events))

    table = Table(title="Журнал событий SWARM", show_header=True)
    table.add_column("Время", style="dim", width=10)
    table.add_column("Задача", style="cyan", width=7)
    table.add_column("Агент", style="green", width=12)
    table.add_column("Событие", width=15)
    table.add_column("Сообщение", style="white")

    event_styles = {
        "task_started": "green",
        "task_done": "blue",
        "task_created": "magenta",
        "task_assigned": "cyan",
        "task_force_closed": "red",
        "file_locked": "yellow",
        "file_unlocked": "yellow",
        "waiting_for_lock": "red",
        "error": "red",
        "agent_registered": "cyan",
        "agent_started": "green",
        "agent_cleanup": "red",
    }

    for event in events:
        # Время
        if event.timestamp:
            time_str = event.timestamp.strftime("%H:%M:%S")
        else:
            time_str = "-"

        # Задача
        task_str = f"#{event.task_id}" if event.task_id else "-"

        # Агент
        agent = agents.get(event.agent_id) if event.agent_id else None
        agent_str = agent.name if agent else "-"

        # Событие
        event_type = event.event.value
        style = event_styles.get(event_type, "white")

        # Сообщение
        msg = event.message or "-"

        table.add_row(
            time_str,
            task_str,
            agent_str,
            f"[{style}]{event_type}[/{style}]",
            msg,
        )

    console.print(table)
    since_str = f", за последние {since}ч" if since else ""
    console.print(f"\n[dim]Показано {len(events)} событий (лимит: {limit}{since_str})[/dim]")

"""
Команда swarm start.

Устанавливает флаг старта для агентов.
"""


import typer
from rich.console import Console

from ..db import find_db_path, get_all_agents, log_event
from ..models import EventType

console = Console()


def _check_db():
    """Проверяет наличие БД."""
    if find_db_path() is None:
        console.print("[red]✗ SWARM не инициализирован. Выполните 'swarm init' сначала.[/red]")
        raise typer.Exit(1)


def start_command(
    all_agents: bool = typer.Option(False, "--all", "-a", help="Запустить всех агентов"),
    agent_name: str | None = typer.Option(None, "--agent", help="Запустить агента по имени"),
    cli_type: str | None = typer.Option(None, "--cli", help="Запустить агентов по типу CLI"),
):
    """
    Сигнализирует агентам о начале работы.
    
    Это информационная команда — агенты должны сами вызвать `swarm next`.
    """
    _check_db()

    agents = get_all_agents()

    if not agents:
        console.print("[yellow]Нет зарегистрированных агентов[/yellow]")
        console.print("Сначала зарегистрируйте агентов через [cyan]swarm join[/cyan]")
        return

    # Фильтруем агентов
    if all_agents:
        target_agents = agents
    elif agent_name:
        target_agents = [a for a in agents if a.name == agent_name]
        if not target_agents:
            console.print(f"[red]✗ Агент '{agent_name}' не найден[/red]")
            raise typer.Exit(1)
    elif cli_type:
        target_agents = [a for a in agents if a.cli_type == cli_type]
        if not target_agents:
            console.print(f"[red]✗ Агенты с типом CLI '{cli_type}' не найдены[/red]")
            raise typer.Exit(1)
    else:
        console.print("[red]✗ Укажите --all, --agent или --cli[/red]")
        raise typer.Exit(1)

    # Логируем событие старта
    for agent in target_agents:
        log_event(
            event=EventType.AGENT_STARTED,
            agent_id=agent.agent_id,
            message="Лидер дал команду начать работу",
        )

    # Выводим список
    console.print(f"\n[green]✓ Команда старта отправлена ({len(target_agents)} агентов)[/green]\n")

    for agent in target_agents:
        console.print(f"  • {agent.name} ({agent.cli_type}/{agent.role})")

    console.print("\n[dim]Агенты должны выполнить [cyan]swarm next[/cyan] для получения задач[/dim]")

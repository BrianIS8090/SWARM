"""
Команды управления агентами.

- swarm join — регистрация агента
- swarm agents — список агентов
- swarm next — получение задачи
- swarm done — завершение задачи
- swarm status — статус агента
"""

import os
import uuid
from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ..db import (
    claim_next_task,
    cleanup_dead_agents,
    complete_task,
    get_all_agents,
    get_current_agent,
    is_process_alive,
    register_agent,
    save_session_token,
    update_agent_heartbeat,
    update_agent_status,
)
from ..models import AgentStatus
from ..utils import CLI_TYPES, VALID_ROLES
from ..utils import check_db as _check_db
from .common import _check_agent

console = Console()


def join_command(
    cli_type: str | None = typer.Option(None, "--cli", "-c", help="Тип CLI (claude/codex/gemini)"),
    name: str | None = typer.Option(None, "--name", "-n", help="Имя агента"),
    role: str | None = typer.Option(None, "--role", "-r", help="Роль (architect/developer/tester/devops)"),
):
    """
    Регистрирует агента в системе SWARM.
    """
    _check_db()

    # Проверяем, не зарегистрирован ли уже
    existing = get_current_agent()
    if existing:
        console.print(
            f"[yellow]⚠ Агент уже зарегистрирован как #{existing.agent_id} "
            f"({existing.cli_type}/{existing.name}/{existing.role})[/yellow]"
        )
        if not typer.confirm("Зарегистрироваться заново?"):
            raise typer.Exit(0)
        # Помечаем старого агента как завершённого, чтобы не оставлять «призрачные» сессии
        update_agent_status(existing.agent_id, AgentStatus.DONE)

    # Запрашиваем данные интерактивно, если не указаны
    if cli_type is None:
        cli_type = Prompt.ask(
            "Тип CLI",
            choices=CLI_TYPES,
            default="claude",
        )
    elif cli_type not in CLI_TYPES:
        console.print(f"[red]✗ Неверный тип CLI. Допустимые: {', '.join(CLI_TYPES)}[/red]")
        raise typer.Exit(1)

    if name is None:
        name = Prompt.ask("Имя агента", default="agent-1")

    if role is None:
        role = Prompt.ask(
            "Роль",
            choices=VALID_ROLES,
            default="developer",
        )
    elif role not in VALID_ROLES:
        console.print(f"[red]✗ Неверная роль. Допустимые: {', '.join(VALID_ROLES)}[/red]")
        raise typer.Exit(1)

    # Генерируем session token
    session_token = str(uuid.uuid4())
    pid = os.getpid()

    # Регистрируем агента
    try:
        agent = register_agent(
            session_token=session_token,
            cli_type=cli_type,
            name=name,
            role=role,
            pid=pid,
        )
    except Exception as e:
        console.print(f"[red]✗ Ошибка регистрации: {e}[/red]")
        raise typer.Exit(1) from None

    # Сохраняем сессию с именем агента (для изоляции между терминалами)
    _, env_command = save_session_token(session_token, name)

    console.print()
    console.print(Panel.fit(
        f"[green]✓ Зарегистрирован как агент #{agent.agent_id}[/green]\n\n"
        f"Тип CLI: [cyan]{cli_type}[/cyan]\n"
        f"Имя: [cyan]{name}[/cyan]\n"
        f"Роль: [cyan]{role}[/cyan]",
        title="SWARM Join",
        border_style="green",
    ))
    console.print()
    
    # Инструкция для установки переменной окружения (для изоляции терминалов)
    console.print("[yellow]⚠ ВАЖНО: Выполни эту команду для привязки терминала к агенту:[/yellow]")
    console.print(f"[cyan]{env_command}[/cyan]")
    console.print()
    console.print("Жди команды Лидера для начала работы.")
    console.print("Затем выполни: [cyan]swarm next[/cyan]")
    console.print()


def agents_command(
    cleanup: bool = typer.Option(False, "--cleanup", help="Удалить неактивных агентов (мёртвые PID + >30 мин heartbeat)"),
    force: bool = typer.Option(False, "--force", help="Удалить ВСЕХ агентов (используй с --cleanup)"),
):
    """
    Показывает список зарегистрированных агентов.
    """
    _check_db()

    if cleanup:
        removed = cleanup_dead_agents(timeout_minutes=30, check_pid=True, force_all=force)
        if removed > 0:
            if force:
                console.print(f"[red]Принудительно удалено агентов: {removed}[/red]")
            else:
                console.print(f"[yellow]Удалено неактивных агентов: {removed}[/yellow]")

    agents = get_all_agents()

    if not agents:
        console.print("[yellow]Зарегистрированных агентов нет[/yellow]")
        return

    table = Table(title="Агенты SWARM", show_header=True)
    table.add_column("ID", style="cyan", width=5)
    table.add_column("CLI", width=8)
    table.add_column("Имя", style="green", width=15)
    table.add_column("Роль", width=12)
    table.add_column("Статус", width=10)
    table.add_column("Задача", width=8)
    table.add_column("Heartbeat", width=15)

    status_colors = {
        AgentStatus.IDLE: "dim",
        AgentStatus.WORKING: "green",
        AgentStatus.WAITING: "yellow",
        AgentStatus.DONE: "blue",
    }

    now = datetime.now(UTC).replace(tzinfo=None)

    for agent in agents:
        color = status_colors.get(agent.status, "white")
        pid_alive = is_process_alive(agent.pid) if agent.pid is not None else None

        # Вычисляем время с последнего heartbeat
        if agent.last_heartbeat:
            delta = now - agent.last_heartbeat
            if delta.total_seconds() < 60:
                hb_str = f"{int(delta.total_seconds())}с назад"
            elif delta.total_seconds() < 3600:
                hb_str = f"{int(delta.total_seconds() / 60)}мин назад"
            else:
                hb_str = f"{int(delta.total_seconds() / 3600)}ч назад"

            # Старый heartbeat — это предупреждение, а не признак смерти процесса
            if delta.total_seconds() > 300 and pid_alive is not True:
                hb_str = f"[red]{hb_str}[/red]"
            elif delta.total_seconds() > 300:
                hb_str = f"[yellow]{hb_str} (PID жив)[/yellow]"
        else:
            hb_str = "-"

        task_str = f"#{agent.current_task_id}" if agent.current_task_id else "-"

        table.add_row(
            f"#{agent.agent_id}",
            agent.cli_type,
            agent.name,
            agent.role,
            f"[{color}]{agent.status.value}[/{color}]",
            task_str,
            hb_str,
        )

    console.print(table)
    console.print(f"\nВсего агентов: {len(agents)}")


def next_command(
    agent_name: str | None = typer.Option(None, "--agent", "-a", help="Имя агента (если не указан — из сессии)"),
):
    """
    Получает следующую задачу для агента.
    """
    agent = _check_agent(agent_name)

    # Обновляем heartbeat
    update_agent_heartbeat(agent.agent_id)

    # Проверяем, нет ли уже активной задачи
    if agent.current_task_id is not None:
        console.print(
            f"[yellow]⚠ У вас уже есть активная задача #{agent.current_task_id}[/yellow]\n"
            "Завершите её командой: [cyan]swarm done --summary \"...\"[/cyan]"
        )
        raise typer.Exit(1)

    # Получаем задачу
    task = claim_next_task(agent)

    if task is None:
        console.print("[yellow]Нет подходящих задач в очереди.[/yellow]")
        console.print("Ожидайте следующей команды Лидера.")
        return

    # Выводим информацию о задаче
    console.print()
    console.print(Panel.fit(
        f"[green]Задача #{task.task_id}[/green] [P{task.priority}]\n\n"
        f"{task.description}",
        title="Новая задача",
        border_style="green",
    ))
    console.print()
    console.print("Следующие шаги:")
    console.print("  1. Определи, какие файлы нужно изменить")
    console.print("  2. Заблокируй один файл: [cyan]swarm lock путь/к/файлу[/cyan]")
    console.print("  3. Выполни правки и сразу разблокируй: [cyan]swarm unlock --file путь/к/файлу[/cyan]")
    console.print("  4. Если работа долгая, обновляй heartbeat: [cyan]swarm heartbeat --quiet[/cyan]")
    console.print("  5. Заверши: [cyan]swarm done --summary \"...\"[/cyan]")
    console.print()


def done_command(
    summary: str = typer.Option(..., "--summary", "-s", help="Резюме выполненной работы"),
    agent_name: str | None = typer.Option(None, "--agent", "-a", help="Имя агента (если не указан — из сессии)"),
):
    """
    Завершает текущую задачу агента.
    """
    agent = _check_agent(agent_name)

    if agent.current_task_id is None:
        console.print("[red]✗ У вас нет активной задачи[/red]")
        raise typer.Exit(1)

    task_id = agent.current_task_id

    # Завершаем задачу
    success = complete_task(agent, summary)

    if success:
        console.print(f"[green]✓ Задача #{task_id} завершена[/green]")
        console.print(f"  Резюме: {summary}")
        console.print()
        console.print("Для получения следующей задачи: [cyan]swarm next[/cyan]")
    else:
        console.print("[red]✗ Ошибка завершения задачи[/red]")
        raise typer.Exit(1)


def status_command(
    agent_name: str | None = typer.Option(None, "--agent", "-a", help="Имя агента (если не указан — из сессии)"),
):
    """
    Показывает статус текущего агента.
    """
    agent = _check_agent(agent_name)

    # Обновляем heartbeat
    update_agent_heartbeat(agent.agent_id)

    status_emoji = {
        AgentStatus.IDLE: "💤",
        AgentStatus.WORKING: "🔄",
        AgentStatus.WAITING: "⏳",
        AgentStatus.DONE: "✓",
    }

    emoji = status_emoji.get(agent.status, "")

    info = [
        f"ID: [cyan]#{agent.agent_id}[/cyan]",
        f"CLI: [cyan]{agent.cli_type}[/cyan]",
        f"Имя: [cyan]{agent.name}[/cyan]",
        f"Роль: [cyan]{agent.role}[/cyan]",
        f"Статус: [green]{emoji} {agent.status.value}[/green]",
    ]

    if agent.current_task_id:
        info.append(f"Текущая задача: [yellow]#{agent.current_task_id}[/yellow]")

    console.print()
    console.print(Panel.fit(
        "\n".join(info),
        title="Статус агента",
        border_style="blue",
    ))
    console.print()


def heartbeat_command(
    agent_name: str | None = typer.Option(None, "--agent", "-a", help="Имя агента (если не указан — из сессии)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Не печатать подтверждение"),
):
    """
    Обновляет heartbeat текущего агента.
    """
    agent = _check_agent(agent_name)
    update_agent_heartbeat(agent.agent_id)

    if not quiet:
        console.print(f"[green]✓ Heartbeat обновлён для агента {agent.name}[/green]")

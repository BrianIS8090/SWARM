"""Команды терминальной оркестрации: swarm terminal ..."""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..db import (
    add_launch_session_agent,
    create_launch_session,
    ensure_terminal_schema,
    get_agent_by_name,
    get_launch_session,
    get_launch_session_agents,
    get_launch_sessions,
    log_event,
    reconcile_launch_session,
    update_launch_agent_status,
    update_launch_session_status,
)
from ..models import EventType, LaunchRegistrationStatus, LaunchSessionStatus
from ..terminal.launcher_registry import launcher_profile
from ..terminal.layouts import launch_layout
from ..terminal.preflight import run_preflight
from ..terminal.prompt_builder import build_bootstrap_prompt
from ..terminal.spec import SPECS_DIR, LaunchSpec, LayoutSpec, load_launch_spec, save_launch_spec
from ..utils import check_db as _check_db

console = Console()

NO_HELP_CONTEXT_SETTINGS = {
    "help_option_names": [],
}

app = typer.Typer(
    help="Терминальная оркестрация агентов",
    add_help_option=False,
    no_args_is_help=False,
    context_settings=NO_HELP_CONTEXT_SETTINGS,
)


def _print_launch_plan(spec) -> None:
    table = Table(title="План запуска терминальных агентов", show_header=True)
    table.add_column("#", width=3, style="cyan")
    table.add_column("CLI", width=10)
    table.add_column("Имя", width=16, style="green")
    table.add_column("Роль", width=12)

    for index, agent in enumerate(spec.agents, start=1):
        table.add_row(str(index), agent.cli, agent.name, agent.role)

    console.print(table)
    console.print(f"layout: [cyan]{spec.layout.mode}[/cyan]")
    console.print(f"режим: [cyan]{spec.approval_mode}[/cyan]")


def _auto_layout_mode(agent_count: int) -> str:
    """Определяет layout mode по количеству агентов."""

    if agent_count <= 1:
        return "single"
    if agent_count <= 4:
        return "mixed"
    return "multi-window"


@app.command("launch", add_help_option=False)
def launch_command(
    spec_path: Path = typer.Option(..., "--spec", help="Путь к launch spec JSON"),
    exclude_cli: str = typer.Option("", "--exclude-cli", help="CLI-тип, который НЕ запускать (вывести команду для пользователя)"),
    yes: bool = typer.Option(False, "--yes", help="Не запрашивать подтверждение"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Проверить и записать сессию без запуска wt"),
):
    """Запускает новую launch-сессию на основе launch spec."""
    _check_db()
    ensure_terminal_schema()

    try:
        spec = load_launch_spec(spec_path)
    except ValueError as exc:
        console.print(f"[red]✗ Ошибка launch spec: {exc}[/red]")
        raise typer.Exit(1) from None

    # Разделяем агентов: запускаемые и исключённые (тот же CLI что у оркестратора)
    excluded_agents = [a for a in spec.agents if exclude_cli and a.cli == exclude_cli]
    launchable_agents = [a for a in spec.agents if not exclude_cli or a.cli != exclude_cli]

    issues = run_preflight(spec, require_wt=not dry_run)
    if issues:
        console.print("[red]✗ Preflight не пройден:[/red]")
        for issue in issues:
            console.print(f"  - {issue}")
        raise typer.Exit(1)

    _print_launch_plan(spec)
    if excluded_agents:
        console.print(f"\n[yellow]⚠ Агенты {exclude_cli} ({len(excluded_agents)} шт.) будут исключены из автозапуска.[/yellow]")

    session_id = f"ls-{uuid.uuid4().hex[:8]}"
    create_launch_session(
        session_id=session_id,
        working_directory=spec.working_directory,
        approval_mode=spec.approval_mode,
        layout_mode=spec.layout.mode,
        requested_agent_count=len(spec.agents),
        created_by="orchestrator",
        status=LaunchSessionStatus.PLANNED,
    )
    log_event(
        EventType.LAUNCH_SESSION_CREATED,
        message=f"Создана launch session {session_id} ({len(spec.agents)} агентов, исключён CLI: {exclude_cli or 'нет'})",
    )

    confirmed = yes or typer.confirm(
        f"Подтвердите запуск {len(spec.agents)} терминальных агентов в таком составе.",
        default=False,
    )

    if not confirmed:
        update_launch_session_status(session_id, LaunchSessionStatus.STOPPED)
        log_event(EventType.LAUNCH_SESSION_STOPPED, message=f"Launch session {session_id} отменена пользователем")
        console.print("[yellow]Запуск отменён пользователем.[/yellow]")
        raise typer.Exit(0)

    update_launch_session_status(session_id, LaunchSessionStatus.APPROVED)
    log_event(EventType.LAUNCH_SESSION_APPROVED, message=f"Launch session {session_id} подтверждена")

    prompt_map: dict[str, str] = {}
    working_dir_path = Path(spec.working_directory)

    for idx, agent in enumerate(spec.agents, start=1):
        prompt = build_bootstrap_prompt(
            cli_type=agent.cli,
            agent_name=agent.name,
            agent_role=agent.role,
            working_directory=working_dir_path,
        )
        prompt_map[agent.name] = prompt
        add_launch_session_agent(
            session_id=session_id,
            cli_type=agent.cli,
            agent_name=agent.name,
            agent_role=agent.role,
            window_index=agent.window if agent.window is not None else 1,
            pane_index=agent.pane if agent.pane is not None else idx,
            launcher_profile=launcher_profile(agent.cli, spec.approval_mode),
            bootstrap_prompt=prompt,
            registration_status=LaunchRegistrationStatus.PLANNED,
        )

    if dry_run:
        update_launch_session_status(session_id, LaunchSessionStatus.STOPPED)
        log_event(EventType.LAUNCH_SESSION_STOPPED, message=f"Launch session {session_id} завершена в dry-run")
        console.print(
            Panel.fit(
                f"[green]✓ Dry-run выполнен[/green]\n\n"
                f"Session ID: [cyan]{session_id}[/cyan]\n"
                "Launch session создана и завершена, терминалы не запускались.",
                title="SWARM Terminal Launch",
                border_style="green",
            )
        )
        # Выводим команду для excluded даже в dry-run
        if excluded_agents:
            _print_excluded_command(spec, excluded_agents, spec_path)
        return

    log_event(EventType.LAUNCH_STARTED, message=f"Старт launch session {session_id}")

    # Запускаем только launchable агентов
    if launchable_agents:
        launch_spec = LaunchSpec(
            version=spec.version,
            working_directory=spec.working_directory,
            approval_mode=spec.approval_mode,
            layout=LayoutSpec(mode=_auto_layout_mode(len(launchable_agents)), max_panes_per_window=spec.layout.max_panes_per_window),
            agents=launchable_agents,
        )
        launch_results = launch_layout(launch_spec, prompt_map, session_id=session_id)
    else:
        launch_results = {}

    for agent in launchable_agents:
        result = launch_results.get(agent.name)
        if result and result.started:
            update_launch_agent_status(
                session_id,
                agent.name,
                LaunchRegistrationStatus.LAUNCHED,
                terminal_pid=result.pid,
            )
            log_event(
                EventType.LAUNCH_AGENT_STARTED,
                message=f"{session_id}: агент {agent.name} ({agent.cli}) запущен",
            )
        else:
            update_launch_agent_status(session_id, agent.name, LaunchRegistrationStatus.FAILED)
            error_message = result.error if result else "неизвестная ошибка запуска"
            log_event(
                EventType.LAUNCH_AGENT_FAILED,
                message=f"{session_id}: агент {agent.name} не запущен ({error_message})",
            )

    started_count = sum(1 for result in launch_results.values() if result.started)
    total_launchable = len(launchable_agents)
    if total_launchable == 0 or started_count == total_launchable:
        update_launch_session_status(session_id, LaunchSessionStatus.LAUNCHED)
    elif started_count == 0 and total_launchable > 0:
        update_launch_session_status(session_id, LaunchSessionStatus.FAILED)
    else:
        update_launch_session_status(session_id, LaunchSessionStatus.PARTIALLY_REGISTERED)

    console.print(
        Panel.fit(
            f"[green]✓ Launch session создана[/green]\n\n"
            f"Session ID: [cyan]{session_id}[/cyan]\n"
            f"Запущено: {started_count}/{total_launchable}"
            + (f", исключено ({exclude_cli}): {len(excluded_agents)}" if excluded_agents else "")
            + "\nПроверьте регистрацию: [cyan]swarm terminal status[/cyan]",
            title="SWARM Terminal Launch",
            border_style="green",
        )
    )

    # Выводим команду для excluded агентов
    if excluded_agents:
        _print_excluded_command(spec, excluded_agents, spec_path)


def _print_excluded_command(spec, excluded_agents, original_spec_path: Path) -> None:
    """Сохраняет excluded-агентов в отдельный spec и выводит команду для пользователя."""

    excluded_spec = LaunchSpec(
        version=spec.version,
        working_directory=spec.working_directory,
        approval_mode=spec.approval_mode,
        layout=LayoutSpec(mode=_auto_layout_mode(len(excluded_agents)), max_panes_per_window=spec.layout.max_panes_per_window),
        agents=excluded_agents,
    )
    specs_dir = Path(spec.working_directory) / SPECS_DIR
    specs_dir.mkdir(parents=True, exist_ok=True)
    excluded_path = specs_dir / f"{original_spec_path.stem}-excluded{original_spec_path.suffix}"
    save_launch_spec(excluded_spec, excluded_path)

    cli_type = excluded_agents[0].cli
    names = ", ".join(a.name for a in excluded_agents)
    console.print()
    console.print(
        Panel.fit(
            f"Агенты [cyan]{cli_type}[/cyan] ({names}) не запущены автоматически.\n"
            f"Spec сохранён: [cyan]{excluded_path}[/cyan]\n\n"
            "Выполните в отдельном окне PowerShell:\n\n"
            f"  [bold green]swarm terminal launch --spec {excluded_path} --yes[/bold green]",
            title=f"Ручной запуск агентов {cli_type}",
            border_style="yellow",
        )
    )


@app.command("status", add_help_option=False)
def status_command():
    """Показывает активные launch-сессии и состояние регистрации."""
    _check_db()
    ensure_terminal_schema()

    sessions = get_launch_sessions()
    if not sessions:
        console.print("[yellow]Launch sessions не найдены.[/yellow]")
        return

    session_table = Table(title="Launch Sessions", show_header=True)
    session_table.add_column("Session", style="cyan")
    session_table.add_column("Статус")
    session_table.add_column("Агенты", justify="right")
    session_table.add_column("Layout")
    session_table.add_column("Режим")

    for session in sessions:
        agents = get_launch_session_agents(session.session_id)
        registered = sum(1 for a in agents if a.registration_status == LaunchRegistrationStatus.REGISTERED)
        session_table.add_row(
            session.session_id,
            session.status.value,
            f"{registered}/{len(agents)}",
            session.layout_mode,
            session.approval_mode,
        )

    console.print(session_table)


@app.command("stop", add_help_option=False)
def stop_command(
    session_id: str = typer.Option(..., "--session", help="ID launch session"),
):
    """Останавливает launch-сессию и закрывает терминалы агентов."""
    _check_db()
    ensure_terminal_schema()

    session = get_launch_session(session_id)
    if session is None:
        console.print(f"[red]✗ Launch session не найдена: {session_id}[/red]")
        raise typer.Exit(1)

    # Читаем PID-файлы, записанные launcher-скриптами (.swarm/pids/{session}_{agent}.pid)
    pid_dir = Path(session.working_directory) / ".swarm" / "pids"
    if not pid_dir.exists():
        pid_dir = Path(session.working_directory) / ".swarm_pids"  # legacy fallback
    killed_count = 0
    if pid_dir.exists():
        for pid_file in pid_dir.glob(f"{session_id}_*.pid"):
            try:
                pid = int(pid_file.read_text().strip())
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, text=True, check=False,
                )
                killed_count += 1
            except (ValueError, OSError):
                pass
            pid_file.unlink(missing_ok=True)

    # Fallback: попробовать PID из БД (для обратной совместимости)
    if killed_count == 0:
        launch_agents = get_launch_session_agents(session_id)
        db_pids = {agent.terminal_pid for agent in launch_agents if agent.terminal_pid}
        for pid in db_pids:
            try:
                os.kill(pid, 15)
                killed_count += 1
            except OSError:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True, text=True, check=False,
                    )
                    killed_count += 1

    update_launch_session_status(session_id, LaunchSessionStatus.STOPPED)
    log_event(EventType.LAUNCH_SESSION_STOPPED, message=f"Launch session {session_id} остановлена ({killed_count} процессов)")
    console.print(f"[green]✓ Launch session {session_id} остановлена (процессов: {killed_count})[/green]")


@app.command("reconcile", add_help_option=False)
def reconcile_command(
    session_id: str = typer.Option(..., "--session", help="ID launch session"),
):
    """Сверяет launch session с фактически зарегистрированными агентами."""
    _check_db()
    ensure_terminal_schema()

    before = {agent.agent_name: agent.registration_status for agent in get_launch_session_agents(session_id)}

    session, launch_agents = reconcile_launch_session(session_id)
    if session is None:
        console.print(f"[red]✗ Launch session не найдена: {session_id}[/red]")
        raise typer.Exit(1)

    table = Table(title=f"Reconcile {session_id}", show_header=True)
    table.add_column("Имя", style="green")
    table.add_column("CLI")
    table.add_column("Роль")
    table.add_column("Статус")
    table.add_column("Agent ID")

    for launch_agent in launch_agents:
        table.add_row(
            launch_agent.agent_name,
            launch_agent.cli_type,
            launch_agent.agent_role,
            launch_agent.registration_status.value,
            str(launch_agent.registered_agent_id or "-"),
        )

    console.print(table)
    console.print(f"Итоговый статус session: [cyan]{session.status.value}[/cyan]")

    if session.status == LaunchSessionStatus.REGISTERED:
        log_event(EventType.LAUNCH_SESSION_COMPLETED, message=f"Launch session {session_id} полностью зарегистрирована")

    for launch_agent in launch_agents:
        previous_status = before.get(launch_agent.agent_name)
        if (
            launch_agent.registration_status == LaunchRegistrationStatus.REGISTERED
            and previous_status != LaunchRegistrationStatus.REGISTERED
        ):
            live_agent = get_agent_by_name(launch_agent.agent_name)
            log_event(
                EventType.LAUNCH_AGENT_REGISTERED,
                agent_id=live_agent.agent_id if live_agent else None,
                message=f"{session_id}: агент {launch_agent.agent_name} зарегистрирован",
            )

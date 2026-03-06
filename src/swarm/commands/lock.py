"""
Команды блокировки файлов.

- swarm lock — захват блокировки
- swarm unlock — снятие блокировки
"""

import time
from pathlib import Path

import typer
from rich.console import Console

from ..db import (
    get_agent_by_name,
    get_agent_lock,
    get_all_agents,
    get_all_locks,
    get_current_agent,
    get_file_lock,
    log_event,
    try_lock_file,
    unlock_file,
    update_agent_heartbeat,
    update_agent_status,
)
from ..models import AgentStatus, EventType
from ..utils import check_db as _check_db

console = Console()


def _check_agent(agent_name: str | None = None):
    """
    Проверяет регистрацию агента.
    
    Args:
        agent_name: Имя агента (если указано, ищет по имени)
    """
    _check_db()
    
    if agent_name:
        agent = get_agent_by_name(agent_name)
    else:
        agent = get_current_agent()
    
    if agent is None:
        if agent_name:
            console.print(f"[red]✗ Агент '{agent_name}' не найден.[/red]")
        else:
            console.print("[red]✗ Агент не зарегистрирован. Выполните 'swarm join' сначала.[/red]")
            console.print("[dim]Подсказка: используйте --agent <имя> для указания агента явно[/dim]")
        raise typer.Exit(1)
    return agent


def lock_command(
    file_path: str = typer.Argument(..., help="Файл для блокировки"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Таймаут ожидания в секундах"),
    agent_name: str | None = typer.Option(None, "--agent", "-a", help="Имя агента (если не указан — из сессии)"),
):
    """
    Захватывает блокировку на указанный файл.
    
    В системе разрешена только одна активная блокировка на агента.
    Если файл занят другим агентом — ждёт его освобождения.
    """
    agent = _check_agent(agent_name)

    if agent.current_task_id is None:
        console.print("[red]✗ У вас нет активной задачи. Сначала выполните 'swarm next'[/red]")
        raise typer.Exit(1)

    task_id = agent.current_task_id
    current_lock = get_agent_lock(agent.agent_id)
    normalized_path = str(Path(file_path).as_posix())

    if current_lock and current_lock.file_path != normalized_path:
        console.print(
            "[red]✗ У агента уже есть активная блокировка.[/red]\n"
            f"Сначала разблокируйте: [cyan]{current_lock.file_path}[/cyan]"
        )
        raise typer.Exit(1)

    if current_lock and current_lock.file_path == normalized_path:
        console.print(f"[yellow]Файл уже заблокирован вами: {file_path}[/yellow]")
        return

    start_time = time.time()
    waiting_logged = False
    sleep_interval = 1.0  # Начальный интервал
    max_sleep = 15.0  # Верхний предел

    while True:
        # Пытаемся захватить блокировку
        if try_lock_file(agent.agent_id, task_id, file_path):
            update_agent_status(agent.agent_id, AgentStatus.WORKING, task_id)
            console.print(f"[green]✓ Заблокирован: {file_path}[/green]")
            return

        # Файл занят — проверяем, кем
        existing_lock = get_file_lock(file_path)

        if existing_lock:
            agents = get_all_agents()
            locker = next(
                (a for a in agents if a.agent_id == existing_lock.locked_by),
                None,
            )
            locker_name = locker.name if locker else f"агент #{existing_lock.locked_by}"

            if not waiting_logged:
                console.print(
                    f"[yellow]⏳ Ожидание: {file_path} "
                    f"(заблокирован {locker_name})[/yellow]"
                )
                log_event(
                    event=EventType.WAITING_FOR_LOCK,
                    agent_id=agent.agent_id,
                    task_id=task_id,
                    message=f"Ожидание блокировки: {file_path}",
                )
                update_agent_status(agent.agent_id, AgentStatus.WAITING, task_id)
                waiting_logged = True

        elapsed = time.time() - start_time
        if elapsed >= timeout:
            console.print(f"[red]✗ Таймаут ожидания: {file_path}[/red]")
            log_event(
                event=EventType.ERROR,
                agent_id=agent.agent_id,
                task_id=task_id,
                message=f"Таймаут блокировки: {file_path}",
            )
            raise typer.Exit(1)

        update_agent_heartbeat(agent.agent_id)
        time.sleep(sleep_interval)
        sleep_interval = min(sleep_interval * 2, max_sleep)


def unlock_command(
    file_path: str = typer.Option(None, "--file", "-f", help="Путь к файлу для разблокировки"),
    force: bool = typer.Option(False, "--force", help="Принудительное снятие (для Лидера)"),
    all_files: bool = typer.Option(False, "--all", "-a", help="Снять все блокировки"),
):
    """
    Снимает блокировку с файла.
    
    --force: принудительное снятие (только для Лидера/оркестратора)
    --all: снять все блокировки
    """
    _check_db()

    if all_files and force:
        # Требуется активная сессия — анонимный процесс без сессии не должен снимать все блокировки
        if get_current_agent() is None:
            console.print("[red]✗ Для --force --all требуется активная сессия агента.[/red]")
            console.print("Зарегистрируйтесь через 'swarm join' и используйте --agent <имя>.")
            raise typer.Exit(1)

        # Снимаем все блокировки
        locks = get_all_locks()
        if not locks:
            console.print("[yellow]Нет активных блокировок[/yellow]")
            return

        for lock in locks:
            unlock_file(lock.file_path, force=True)
            log_event(
                event=EventType.FILE_UNLOCKED,
                task_id=lock.task_id,
                agent_id=lock.locked_by,
                message=f"Принудительно разблокирован файл: {lock.file_path}",
            )
            console.print(f"[green]✓ Разблокирован: {lock.file_path}[/green]")

        console.print(f"\n[green]Снято блокировок: {len(locks)}[/green]")
        return

    if file_path is None:
        console.print("[red]✗ Укажите файл: --file <путь>[/red]")
        raise typer.Exit(1)

    if force:
        # Требуется активная сессия для принудительного снятия блокировки
        if get_current_agent() is None:
            console.print("[red]✗ Для --force требуется активная сессия агента.[/red]")
            console.print("Зарегистрируйтесь через 'swarm join' и используйте --agent <имя>.")
            raise typer.Exit(1)

        # Принудительное снятие
        existing = get_file_lock(file_path)
        if existing is None:
            console.print(f"[yellow]Файл {file_path} не заблокирован[/yellow]")
            return

        unlock_file(file_path, force=True)
        log_event(
            event=EventType.FILE_UNLOCKED,
            task_id=existing.task_id,
            agent_id=existing.locked_by,
            message=f"Принудительно разблокирован файл: {file_path}",
        )
        console.print(f"[green]✓ Принудительно разблокирован: {file_path}[/green]")
    else:
        # Обычное снятие — только своих блокировок
        agent = _check_agent()

        if unlock_file(file_path, agent_id=agent.agent_id):
            log_event(
                event=EventType.FILE_UNLOCKED,
                task_id=agent.current_task_id,
                agent_id=agent.agent_id,
                message=f"Разблокирован файл: {file_path}",
            )
            update_agent_heartbeat(agent.agent_id)
            console.print(f"[green]✓ Разблокирован: {file_path}[/green]")
        else:
            console.print(f"[red]✗ Не удалось разблокировать: {file_path}[/red]")
            existing = get_file_lock(file_path)
            if existing:
                console.print("Файл заблокирован другим агентом. Снять его может только владелец, Лидер или оркестратор.")
            else:
                console.print("Файл не заблокирован.")
            raise typer.Exit(1)

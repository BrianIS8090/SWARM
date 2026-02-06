"""
Команды блокировки файлов.

- swarm lock — захват блокировки
- swarm unlock — снятие блокировки
"""

import time

import typer
from rich.console import Console

from ..db import (
    find_db_path,
    get_agent_by_name,
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

console = Console()


def _check_db():
    """Проверяет наличие БД."""
    if find_db_path() is None:
        console.print("[red]✗ SWARM не инициализирован. Выполните 'swarm init' сначала.[/red]")
        raise typer.Exit(1)


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
    files: list[str] = typer.Argument(..., help="Файлы для блокировки"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Таймаут ожидания в секундах"),
    agent_name: str | None = typer.Option(None, "--agent", "-a", help="Имя агента (если не указан — из сессии)"),
):
    """
    Захватывает блокировки на указанные файлы.
    
    Если файл занят другим агентом — ждёт его освобождения.
    """
    agent = _check_agent(agent_name)

    if agent.current_task_id is None:
        console.print("[red]✗ У вас нет активной задачи. Сначала выполните 'swarm next'[/red]")
        raise typer.Exit(1)

    task_id = agent.current_task_id

    # Сортируем файлы для предотвращения дедлоков
    sorted_files = sorted(files)

    locked_files = []
    failed_files = []

    for file_path in sorted_files:
        start_time = time.time()
        waiting_logged = False

        while True:
            # Пытаемся захватить блокировку
            if try_lock_file(agent.agent_id, task_id, file_path):
                locked_files.append(file_path)
                console.print(f"[green]✓ Заблокирован: {file_path}[/green]")
                break

            # Файл занят — проверяем, кем
            existing_lock = get_file_lock(file_path)

            if existing_lock:
                # Находим агента
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
                    # Логируем ожидание
                    log_event(
                        event=EventType.WAITING_FOR_LOCK,
                        agent_id=agent.agent_id,
                        task_id=task_id,
                        message=f"Ожидание блокировки: {file_path}",
                    )
                    # Обновляем статус
                    update_agent_status(agent.agent_id, AgentStatus.WAITING, task_id)
                    waiting_logged = True

            # Проверяем таймаут
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                console.print(f"[red]✗ Таймаут ожидания: {file_path}[/red]")
                log_event(
                    event=EventType.ERROR,
                    agent_id=agent.agent_id,
                    task_id=task_id,
                    message=f"Таймаут блокировки: {file_path}",
                )
                failed_files.append(file_path)
                break

            # Обновляем heartbeat
            update_agent_heartbeat(agent.agent_id)

            # Ждём перед повторной попыткой
            time.sleep(3)

    # Возвращаем статус working если были в waiting
    if locked_files:
        update_agent_status(agent.agent_id, AgentStatus.WORKING, task_id)

    # Итог
    if locked_files:
        console.print(f"\n[green]Заблокировано: {len(locked_files)} файлов[/green]")

    if failed_files:
        console.print(f"[red]Не удалось заблокировать: {len(failed_files)} файлов[/red]")
        raise typer.Exit(1)


def unlock_command(
    file_path: str = typer.Option(None, "--file", "-f", help="Путь к файлу для разблокировки"),
    force: bool = typer.Option(False, "--force", help="Принудительное снятие (для Лидера)"),
    all_files: bool = typer.Option(False, "--all", "-a", help="Снять все блокировки"),
):
    """
    Снимает блокировку с файла.
    
    --force: принудительное снятие (для Лидера)
    --all: снять все блокировки
    """
    _check_db()

    if all_files and force:
        # Снимаем все блокировки
        locks = get_all_locks()
        if not locks:
            console.print("[yellow]Нет активных блокировок[/yellow]")
            return

        for lock in locks:
            unlock_file(lock.file_path, force=True)
            console.print(f"[green]✓ Разблокирован: {lock.file_path}[/green]")

        console.print(f"\n[green]Снято блокировок: {len(locks)}[/green]")
        return

    if file_path is None:
        console.print("[red]✗ Укажите файл: --file <путь>[/red]")
        raise typer.Exit(1)

    if force:
        # Принудительное снятие
        existing = get_file_lock(file_path)
        if existing is None:
            console.print(f"[yellow]Файл {file_path} не заблокирован[/yellow]")
            return

        unlock_file(file_path, force=True)
        console.print(f"[green]✓ Принудительно разблокирован: {file_path}[/green]")
    else:
        # Обычное снятие — только своих блокировок
        agent = _check_agent()

        if unlock_file(file_path, agent_id=agent.agent_id):
            console.print(f"[green]✓ Разблокирован: {file_path}[/green]")
        else:
            console.print(f"[red]✗ Не удалось разблокировать: {file_path}[/red]")
            console.print("Возможно, файл заблокирован другим агентом или не заблокирован вообще")
            raise typer.Exit(1)

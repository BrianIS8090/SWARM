"""
Команды управления задачами.

- swarm task add — создание задачи
- swarm task list — список задач
"""


import typer
from rich.console import Console

from ..db import (
    assign_task_to_agent,
    create_task,
    force_close_task,
    get_all_tasks,
    get_current_agent,
    get_task,
    log_event,
    reset_task,
)
from ..models import EventType, TaskStatus
from ..utils import check_db as _check_db

NO_HELP_CONTEXT_SETTINGS = {
    "help_option_names": [],
}

app = typer.Typer(
    help="Управление задачами",
    add_help_option=False,
    no_args_is_help=False,
    context_settings=NO_HELP_CONTEXT_SETTINGS,
)
console = Console()


def _ensure_leader_context():
    """Запрещает агенту выполнять команды оркестратора."""
    agent = get_current_agent()
    if agent is not None:
        console.print("[red]✗ Агент не может изменять очередь задач.[/red]")
        console.print("Создание, переназначение и принудительное закрытие задач доступны только Лидеру или оркестратору.")
        raise typer.Exit(1)


@app.command(name="add", add_help_option=False)
def add_command(
    desc: str = typer.Option(..., "--desc", "-d", help="Описание задачи"),
    priority: int = typer.Option(3, "--priority", "-p", help="Приоритет (1-5, где 1 — наивысший)"),
    cli: str | None = typer.Option(None, "--cli", help="Фильтр по типу CLI"),
    name: str | None = typer.Option(None, "--name", help="Фильтр по имени агента"),
    role: str | None = typer.Option(None, "--role", help="Фильтр по роли агента"),
    depends_on: int | None = typer.Option(None, "--depends-on", help="ID задачи-зависимости"),
):
    """
    Создаёт новую задачу в очереди.
    """
    _check_db()
    _ensure_leader_context()

    # Валидация приоритета
    if priority < 1 or priority > 5:
        console.print("[red]✗ Приоритет должен быть от 1 до 5[/red]")
        raise typer.Exit(1)

    # Валидация зависимости
    if depends_on is not None:
        dep_task = get_task(depends_on)
        if dep_task is None:
            console.print(f"[red]✗ Задача #{depends_on} не найдена[/red]")
            raise typer.Exit(1)

    # Создаём задачу
    try:
        task = create_task(
            description=desc,
            priority=priority,
            target_cli=cli,
            target_name=name,
            target_role=role,
            depends_on=depends_on,
        )
    except Exception as e:
        console.print(f"[red]✗ Ошибка создания задачи: {e}[/red]")
        raise typer.Exit(1)

    # Логируем создание задачи
    target_parts = []
    if cli:
        target_parts.append(f"cli={cli}")
    if name:
        target_parts.append(f"name={name}")
    if role:
        target_parts.append(f"role={role}")
    target_str = f" ({', '.join(target_parts)})" if target_parts else ""
    dep_str = f" [depends on #{depends_on}]" if depends_on else ""

    log_event(
        event=EventType.TASK_CREATED,
        task_id=task.task_id,
        message=f"[P{priority}]{target_str}{dep_str} {desc}",
    )

    console.print(
        f"[green]✓ Задача #{task.task_id} создана[/green] "
        f"[P{priority}]{target_str}{dep_str}"
    )
    console.print(f"  {desc}")


@app.command(name="list", add_help_option=False)
def list_command(
    status: str | None = typer.Option(None, "--status", "-s", help="Фильтр: pending, in_progress, done, blocked"),
    agent: int | None = typer.Option(None, "--agent", "-a", help="Фильтр по ID агента"),
    priority: int | None = typer.Option(None, "--priority", "-p", help="Фильтр по приоритету"),
    show_all: bool = typer.Option(False, "--all", help="Показать ВСЕ задачи (включая done)"),
):
    """
    Показывает список задач с полным описанием.
    
    По умолчанию показывает только активные задачи (pending, in_progress, blocked).
    Используйте --all для показа всех задач включая завершённые.
    """
    _check_db()

    # Парсим статус
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            valid = ", ".join([s.value for s in TaskStatus])
            console.print(f"[red]✗ Неверный статус. Допустимые значения: {valid}[/red]")
            raise typer.Exit(1)

    # Получаем все задачи один раз для статистики и отображения (m-6)
    all_tasks = get_all_tasks()

    # Применяем фильтры
    tasks = all_tasks
    if task_status:
        tasks = [t for t in tasks if t.status == task_status]
    if agent is not None:
        tasks = [t for t in tasks if t.assigned_to == agent]
    if priority is not None:
        tasks = [t for t in tasks if t.priority == priority]

    # Фильтруем завершённые если не указан --all
    if not show_all and task_status is None:
        tasks = [t for t in tasks if t.status != TaskStatus.DONE]

    if not tasks:
        console.print("[yellow]Задач не найдено[/yellow]")
        return

    # Считаем статистику
    pending_count = len([t for t in all_tasks if t.status == TaskStatus.PENDING])
    progress_count = len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS])
    done_count = len([t for t in all_tasks if t.status == TaskStatus.DONE])
    blocked_count = len([t for t in all_tasks if t.status == TaskStatus.BLOCKED])

    # Заголовок со статистикой
    console.print()
    console.print(f"[bold]Статистика:[/bold] "
                  f"[yellow]⏳ Ожидают: {pending_count}[/yellow] | "
                  f"[green]🔄 В работе: {progress_count}[/green] | "
                  f"[dim]✓ Завершено: {done_count}[/dim] | "
                  f"[red]🚫 Заблок.: {blocked_count}[/red]")
    console.print()

    status_colors = {
        TaskStatus.PENDING: "yellow",
        TaskStatus.IN_PROGRESS: "green",
        TaskStatus.DONE: "dim",
        TaskStatus.BLOCKED: "red",
    }

    status_icons = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.IN_PROGRESS: "🔄",
        TaskStatus.DONE: "✓",
        TaskStatus.BLOCKED: "🚫",
    }

    # Выводим задачи в виде списка с полным описанием
    for task in tasks:
        color = status_colors.get(task.status, "white")
        icon = status_icons.get(task.status, "")

        # Назначен (кому Лидер назначил)
        assigned_str = f"→ [cyan]{task.target_name}[/cyan]" if task.target_name else ""
        
        # Работает (кто выполняет)
        working_str = f"[выполняет #{task.assigned_to}]" if task.assigned_to else ""

        # Заголовок задачи
        console.print(f"[bold cyan]#{task.task_id}[/bold cyan] [P{task.priority}] "
                      f"[{color}]{icon} {task.status.value}[/{color}] "
                      f"{assigned_str} {working_str}")
        
        # Полное описание
        console.print(f"    {task.description}")
        
        # Дополнительная информация
        info_parts = []
        if task.target_cli:
            info_parts.append(f"cli:{task.target_cli}")
        if task.target_role:
            info_parts.append(f"role:{task.target_role}")
        if task.depends_on:
            info_parts.append(f"зависит от #{task.depends_on}")
        
        if info_parts:
            console.print(f"    [dim]{', '.join(info_parts)}[/dim]")
        
        # Резюме отдельной строкой (полное)
        if task.summary:
            console.print(f"    [green]Резюме: {task.summary}[/green]")
        
        console.print()

    console.print(f"[dim]Показано: {len(tasks)} задач[/dim]")


@app.command(name="close", add_help_option=False)
def close_command(
    task_id: int = typer.Argument(..., help="ID задачи для закрытия"),
    reason: str = typer.Option(
        "Принудительно закрыта Лидером",
        "--reason", "-r",
        help="Причина закрытия",
    ),
):
    """
    Принудительно завершает задачу (команда для Лидера).
    
    Освобождает блокировки файлов и агента.
    """
    _check_db()
    _ensure_leader_context()
    
    # Проверяем существование задачи
    task = get_task(task_id)
    if task is None:
        console.print(f"[red]✗ Задача #{task_id} не найдена[/red]")
        raise typer.Exit(1)
    
    # Проверяем, не завершена ли уже
    if task.status == TaskStatus.DONE:
        console.print(f"[yellow]Задача #{task_id} уже завершена[/yellow]")
        return
    
    # Закрываем задачу
    success = force_close_task(task_id, reason)

    if success:
        # КРИТ-5: log_event уже вызывается внутри force_close_task (TASK_FORCE_CLOSED),
        # повторный вызов здесь убран для предотвращения двойного логирования
        console.print(f"[green]✓ Задача #{task_id} принудительно закрыта[/green]")
        console.print(f"  Причина: {reason}")

        if task.assigned_to:
            console.print(f"  Агент #{task.assigned_to} освобождён")
    else:
        console.print(f"[red]✗ Ошибка закрытия задачи #{task_id}[/red]")
        raise typer.Exit(1)


@app.command(name="reset", add_help_option=False)
def reset_command(
    task_id: int = typer.Argument(..., help="ID задачи для сброса"),
):
    """
    Сбрасывает задачу в статус pending.

    Снимает привязку к агенту (target_name, assigned_to),
    освобождает блокировки файлов.
    """
    _check_db()
    _ensure_leader_context()

    # Проверяем существование задачи
    task = get_task(task_id)
    if task is None:
        console.print(f"[red]✗ Задача #{task_id} не найдена[/red]")
        raise typer.Exit(1)

    # Проверяем, не в pending ли уже
    if task.status == TaskStatus.PENDING and task.assigned_to is None and task.target_name is None:
        console.print(f"[yellow]Задача #{task_id} уже в статусе pending[/yellow]")
        return

    # Сбрасываем задачу
    success = reset_task(task_id)

    if success:
        # КРИТ-5: log_event уже вызывается внутри reset_task (TASK_RESET),
        # повторный вызов здесь убран для предотвращения двойного логирования
        console.print(f"[green]✓ Задача #{task_id} сброшена в pending[/green]")

        if task.assigned_to:
            console.print(f"  Агент #{task.assigned_to} освобождён")
        if task.target_name:
            console.print(f"  Привязка к '{task.target_name}' снята")
    else:
        console.print(f"[red]✗ Ошибка сброса задачи #{task_id}[/red]")
        raise typer.Exit(1)


@app.command(name="assign", add_help_option=False)
def assign_command(
    task_id: int = typer.Argument(..., help="ID задачи"),
    agent: str = typer.Option(..., "--agent", "-a", help="Имя агента"),
):
    """
    Назначает задачу конкретному агенту.
    
    После назначения только этот агент сможет получить задачу через 'swarm next'.
    """
    _check_db()
    _ensure_leader_context()
    
    # Проверяем существование задачи
    task = get_task(task_id)
    if task is None:
        console.print(f"[red]✗ Задача #{task_id} не найдена[/red]")
        raise typer.Exit(1)
    
    # Проверяем статус
    if task.status == TaskStatus.DONE:
        console.print(f"[yellow]Задача #{task_id} уже завершена[/yellow]")
        return
    
    if task.status == TaskStatus.IN_PROGRESS:
        console.print(f"[yellow]Задача #{task_id} уже выполняется агентом #{task.assigned_to}[/yellow]")
        return
    
    # Назначаем
    success = assign_task_to_agent(task_id, agent)

    if success:
        log_event(
            event=EventType.TASK_ASSIGNED,
            task_id=task_id,
            message=f"Задача назначена агенту '{agent}'",
        )
        console.print(f"[green]✓ Задача #{task_id} назначена агенту '{agent}'[/green]")
        console.print(f"  Только '{agent}' сможет получить эту задачу через 'swarm next'")
    else:
        console.print(f"[red]✗ Ошибка назначения задачи #{task_id}[/red]")
        raise typer.Exit(1)

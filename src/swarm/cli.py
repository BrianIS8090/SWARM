"""
Главный модуль CLI для SWARM.

Точка входа для всех команд:
- swarm init — инициализация среды
- swarm task — управление задачами
- swarm join — регистрация агента
- swarm agents — список агентов
- swarm next — получение следующей задачи
- swarm lock — блокировка файлов
- swarm done — завершение задачи
- swarm status — статус агента
- swarm monitor — live-дашборд
- swarm tui — TUI-монитор со скроллингом
- swarm start — запуск агентов
- swarm unlock — снятие блокировок
"""

import typer
from rich.console import Console

from .commands import agent, init, lock, logs, monitor, start, task, tui

# Создаём главное приложение
app = typer.Typer(
    name="swarm",
    help="SWARM — Система оркестрации мультиагентной среды для LLM-агентов",
    add_completion=False,
    no_args_is_help=True,
)

# Консоль для вывода
console = Console()

# Регистрируем подкоманды
app.command(name="init", help="Инициализирует среду SWARM в текущей директории")(init.init_command)
app.add_typer(task.app, name="task", help="Управление задачами")
app.command(name="join", help="Регистрирует агента в системе")(agent.join_command)
app.command(name="agents", help="Показывает список зарегистрированных агентов")(agent.agents_command)
app.command(name="next", help="Получает следующую задачу для агента")(agent.next_command)
app.command(name="done", help="Завершает текущую задачу агента")(agent.done_command)
app.command(name="status", help="Показывает статус текущего агента")(agent.status_command)
app.command(name="lock", help="Захватывает блокировки на файлы")(lock.lock_command)
app.command(name="unlock", help="Снимает блокировку с файла")(lock.unlock_command)
app.command(name="start", help="Сигнализирует агентам о начале работы")(start.start_command)
app.command(name="monitor", help="Запускает live-дашборд мониторинга")(monitor.monitor_command)
app.command(name="tui", help="Запускает TUI-монитор со скроллингом")(tui.run_tui)
app.command(name="logs", help="Показывает журнал событий")(logs.logs_command)


def main():
    """Точка входа CLI."""
    app()


if __name__ == "__main__":
    main()

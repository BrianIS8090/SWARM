"""
Главный модуль CLI для SWARM.

Точка входа для всех команд:
- swarm init — инициализация среды
- swarm path — настройка PATH для CLI
- swarm task — управление задачами
- swarm join — регистрация агента
- swarm agents — список агентов
- swarm next — получение следующей задачи
- swarm lock — блокировка файлов
- swarm done — завершение задачи
- swarm status — статус агента
- swarm heartbeat — обновление heartbeat агента
- swarm monitor — live-дашборд
- swarm tui — TUI-монитор со скроллингом
- swarm start — запуск агентов
- swarm unlock — снятие блокировок
"""

import typer

from .commands import agent, init, lock, logs, monitor, path_cmd, start, task, terminal, tui
from .utils import create_console, get_version

NO_HELP_CONTEXT_SETTINGS = {
    "help_option_names": [],
}

# Создаём главное приложение
app = typer.Typer(
    name="swarm",
    help=f"SWARM v{get_version()} — Система оркестрации мультиагентной среды для LLM-агентов",
    add_completion=False,
    no_args_is_help=False,
    add_help_option=False,
    context_settings=NO_HELP_CONTEXT_SETTINGS,
)

# Консоль для вывода
console = create_console()

# Регистрируем подкоманды
app.command(name="init", help="Инициализирует среду SWARM в текущей директории", add_help_option=False)(
    init.init_command
)
app.add_typer(
    task.app,
    name="task",
    help="Управление задачами",
    add_help_option=False,
    no_args_is_help=False,
    context_settings=NO_HELP_CONTEXT_SETTINGS,
)
app.command(name="join", help="Регистрирует агента в системе", add_help_option=False)(agent.join_command)
app.command(name="agents", help="Показывает список зарегистрированных агентов", add_help_option=False)(
    agent.agents_command
)
app.command(name="next", help="Получает следующую задачу для агента", add_help_option=False)(agent.next_command)
app.command(name="done", help="Завершает текущую задачу агента", add_help_option=False)(agent.done_command)
app.command(name="status", help="Показывает статус текущего агента", add_help_option=False)(agent.status_command)
app.command(name="heartbeat", help="Обновляет heartbeat текущего агента", add_help_option=False)(
    agent.heartbeat_command
)
app.command(name="lock", help="Захватывает блокировки на файлы", add_help_option=False)(lock.lock_command)
app.command(name="unlock", help="Снимает блокировку с файла", add_help_option=False)(lock.unlock_command)
app.command(name="start", help="Сигнализирует агентам о начале работы", add_help_option=False)(start.start_command)
app.command(name="monitor", help="Запускает live-дашборд мониторинга", add_help_option=False)(monitor.monitor_command)
app.command(name="path", help="Добавляет пользовательский Python Scripts в PATH", add_help_option=False)(path_cmd.path_command)
app.command(name="tui", help="Запускает TUI-монитор со скроллингом", add_help_option=False)(tui.run_tui)
app.command(name="logs", help="Показывает журнал событий", add_help_option=False)(logs.logs_command)
app.add_typer(
    terminal.app,
    name="terminal",
    help="Терминальная оркестрация агентов",
    add_help_option=False,
    no_args_is_help=False,
    context_settings=NO_HELP_CONTEXT_SETTINGS,
)


def main():
    """Точка входа CLI."""
    app()


if __name__ == "__main__":
    main()

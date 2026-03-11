"""
Общие утилиты для команд SWARM.

Содержит переиспользуемые функции, которые нужны нескольким модулям команд.
"""

import typer
from rich.console import Console

from ..db import get_agent_by_name, get_current_agent
from ..utils import check_db as _check_db

console = Console()


def _check_agent(agent_name: str | None = None):
  """
  Проверяет регистрацию агента.

  Args:
      agent_name: Имя агента (если указано, ищет по имени вместо сессии)

  Returns:
      Agent: Найденный агент

  Raises:
      typer.Exit: Если агент не найден
  """
  _check_db()

  if agent_name:
    # Ищем агента по имени напрямую
    agent = get_agent_by_name(agent_name)
  else:
    # Ищем по сессии (переменная окружения или файл)
    agent = get_current_agent()

  if agent is None:
    if agent_name:
      console.print(f"[red]✗ Агент '{agent_name}' не найден.[/red]")
    else:
      console.print("[red]✗ Агент не зарегистрирован. Выполните 'swarm join' сначала.[/red]")
      console.print("[dim]Подсказка: используйте --agent <имя> для указания агента явно[/dim]")
    raise typer.Exit(1)
  return agent

"""
Общие утилиты SWARM.
"""

import json
from pathlib import Path

import typer
from rich.console import Console

from .db import find_db_path

console = Console()

# Типы CLI-агентов (единственный источник правды)
CLI_TYPES = ["claude", "codex", "gemini", "opencode", "qwen"]


def get_version() -> str:
  """Читает версию из version.json."""
  version_file = Path(__file__).parent / "version.json"
  data = json.loads(version_file.read_text(encoding="utf-8"))
  return data["version"]


def check_db():
  """Проверяет наличие БД. Завершает процесс, если не найдена."""
  if find_db_path() is None:
    console.print("[red]✗ SWARM не инициализирован. Выполните 'swarm init' сначала.[/red]")
    raise typer.Exit(1)

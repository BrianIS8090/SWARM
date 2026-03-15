"""
Общие утилиты SWARM.
"""

import functools
import json
import sys
from pathlib import Path

import typer
from rich.console import Console

from .db import find_db_path

def _configure_stdio_for_unicode() -> None:
  """Переключает stdout/stderr на UTF-8, чтобы Rich не падал на Unicode в Windows-консолях."""
  for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream is None:
      continue

    reconfigure = getattr(stream, "reconfigure", None)
    encoding = getattr(stream, "encoding", None)
    if callable(reconfigure) and encoding and encoding.lower() != "utf-8":
      reconfigure(encoding="utf-8")


def create_console() -> Console:
  """Создаёт Rich Console после безопасной настройки кодировки потоков."""
  _configure_stdio_for_unicode()
  return Console()


console = create_console()

# Типы CLI-агентов (единственный источник правды)
CLI_TYPES = ["claude", "codex", "gemini", "opencode", "qwen"]

# Допустимые роли агентов (единственный источник правды)
VALID_ROLES = ["architect", "developer", "tester", "devops"]


@functools.lru_cache(maxsize=1)
def get_version() -> str:
  """Читает версию из version.json. Результат кешируется."""
  try:
    version_file = Path(__file__).parent / "version.json"
    data = json.loads(version_file.read_text(encoding="utf-8"))
    return data["version"]
  except (FileNotFoundError, KeyError, json.JSONDecodeError, Exception):
    return "unknown"


def check_db():
  """Проверяет наличие БД. Завершает процесс, если не найдена."""
  if find_db_path() is None:
    console.print("[red]✗ SWARM не инициализирован. Выполните 'swarm init' сначала.[/red]")
    raise typer.Exit(1)

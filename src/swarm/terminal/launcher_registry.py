"""Реестр PowerShell launchers для CLI-агентов."""

from __future__ import annotations

from pathlib import Path


def get_launchers_dir() -> Path:
    """Возвращает директорию встроенных launchers."""

    return Path(__file__).resolve().parent.parent / "resources" / "launchers"


def get_launcher_path(cli_type: str, approval_mode: str) -> Path:
    """Возвращает путь к launcher-скрипту по CLI и режиму."""

    filename = f"{cli_type}-{approval_mode}-launch.ps1"
    return get_launchers_dir() / filename


def launcher_profile(cli_type: str, approval_mode: str) -> str:
    """Возвращает имя профиля launcher для записи в БД."""

    return f"{cli_type}-{approval_mode}"

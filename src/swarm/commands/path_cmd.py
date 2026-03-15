"""
Команда swarm path.

Управляет добавлением пользовательского каталога Python Scripts в PATH на Windows.
"""

from __future__ import annotations

import ctypes
import os
import sys
import sysconfig
from typing import Final

import typer

from ..utils import create_console

console = create_console()

WINDOWS_ENV_KEY: Final[str] = "Environment"
PATH_VALUE_NAME: Final[str] = "Path"
HWND_BROADCAST: Final[int] = 0xFFFF
WM_SETTINGCHANGE: Final[int] = 0x001A
SMTO_ABORTIFHUNG: Final[int] = 0x0002


def _get_user_scripts_dir() -> str:
    """Возвращает каталог Scripts для пользовательской схемы установки Python."""
    return os.path.normpath(sysconfig.get_path("scripts", scheme="nt_user"))


def _split_path_entries(raw_path: str) -> list[str]:
    """Разбивает PATH на элементы без пустых сегментов."""
    return [entry for entry in raw_path.split(os.pathsep) if entry]


def _contains_path_entry(raw_path: str, target: str) -> bool:
    """Проверяет наличие target в PATH без учёта регистра и слэшей."""
    normalized_target = os.path.normcase(os.path.normpath(target))
    return any(
        os.path.normcase(os.path.normpath(entry)) == normalized_target
        for entry in _split_path_entries(raw_path)
    )


def _read_user_path_windows() -> str:
    """Читает пользовательский PATH из реестра Windows."""
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_ENV_KEY, 0, winreg.KEY_READ) as key:
        try:
            value, _ = winreg.QueryValueEx(key, PATH_VALUE_NAME)
        except FileNotFoundError:
            return ""
    return value


def _write_user_path_windows(new_path: str) -> None:
    """Записывает пользовательский PATH в реестр Windows."""
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_ENV_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, PATH_VALUE_NAME, 0, winreg.REG_EXPAND_SZ, new_path)


def _broadcast_environment_change() -> None:
    """Уведомляет Windows о том, что переменные окружения изменились."""
    user32 = getattr(ctypes, "windll", None)
    if user32 is None:
        return

    send_message = getattr(user32.user32, "SendMessageTimeoutW", None)
    if send_message is None:
        return

    try:
        send_message(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            None,
        )
    except Exception:
        # Даже если broadсast не удался, PATH уже записан в реестр.
        pass


def path_command(
    check: bool = typer.Option(False, "--check", help="Только проверить, есть ли путь в PATH"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Показать изменения без записи в PATH"),
):
    """
    Добавляет пользовательский каталог Python Scripts в PATH на Windows.

    Полезно после `pip install -e .`, если команда `swarm` не находится в PowerShell.
    """
    if sys.platform != "win32":
        console.print("[yellow]Команда swarm path сейчас поддерживается только на Windows.[/yellow]")
        raise typer.Exit(1)

    scripts_dir = _get_user_scripts_dir()
    user_path = _read_user_path_windows()
    in_user_path = _contains_path_entry(user_path, scripts_dir)
    in_session_path = _contains_path_entry(os.environ.get("PATH", ""), scripts_dir)

    if check:
        if in_user_path:
            console.print(f"[green]✓ Каталог уже есть в пользовательском PATH:[/green] [cyan]{scripts_dir}[/cyan]")
        else:
            console.print(f"[yellow]⚠ Каталог отсутствует в пользовательском PATH:[/yellow] [cyan]{scripts_dir}[/cyan]")

        if in_session_path:
            console.print("[green]✓ Текущий терминал уже видит этот путь.[/green]")
        else:
            console.print("[yellow]⚠ Текущий терминал ещё не видит этот путь.[/yellow]")
        return

    if in_user_path:
        console.print(f"[green]✓ Каталог уже есть в пользовательском PATH:[/green] [cyan]{scripts_dir}[/cyan]")
        if not in_session_path:
            os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + scripts_dir
            console.print("[green]✓ Путь добавлен в текущую сессию терминала.[/green]")
        return

    new_user_path = os.pathsep.join([*filter(None, [user_path, scripts_dir])])

    if dry_run:
        console.print("[bold]Dry run:[/bold] будет добавлен путь в пользовательский PATH:")
        console.print(f"  [cyan]{scripts_dir}[/cyan]")
        return

    _write_user_path_windows(new_user_path)
    _broadcast_environment_change()

    if in_session_path:
        os.environ["PATH"] = os.environ.get("PATH", "")
    else:
        os.environ["PATH"] = os.pathsep.join([*filter(None, [os.environ.get("PATH", ""), scripts_dir])])

    console.print(f"[green]✓ Каталог добавлен в пользовательский PATH:[/green] [cyan]{scripts_dir}[/cyan]")
    console.print("[green]✓ Текущая сессия обновлена.[/green]")
    console.print("Новые окна PowerShell/Windows Terminal подхватят PATH автоматически.")

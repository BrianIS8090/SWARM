"""Preflight-проверки перед запуском терминальных агентов."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..db import get_active_launch_agent_names, get_all_agents
from ..models import AgentStatus
from .launcher_registry import get_launcher_path
from .spec import LaunchSpec

# Статусы агентов, которые считаются завершёнными (не блокируют перезапуск)
_INACTIVE_STATUSES = {AgentStatus.DONE, AgentStatus.UNKNOWN}


def _find_cli_binary(cli_type: str) -> str | None:
    """Пытается найти исполняемый файл CLI-агента."""

    candidates = [cli_type]
    if cli_type == "claude":
        candidates.extend(["claude.exe"])
    elif cli_type in {"codex", "gemini", "opencode", "qwen"}:
        candidates.extend([f"{cli_type}.cmd", f"{cli_type}.ps1"])

    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def run_preflight(spec: LaunchSpec, require_wt: bool = True) -> list[str]:
    """Выполняет preflight-проверки и возвращает список ошибок."""

    issues: list[str] = []

    workdir = Path(spec.working_directory)
    if not workdir.exists() or not workdir.is_dir():
        issues.append(f"Рабочая директория не существует: {workdir}")

    if require_wt and shutil.which("wt") is None and shutil.which("wt.exe") is None:
        issues.append("Не найден Windows Terminal (wt.exe) в PATH")

    requested_names = {agent.name for agent in spec.agents}
    # Игнорируем агентов с завершёнными статусами (DONE, UNKNOWN) — они не блокируют перезапуск
    active_registered_names = {
      agent.name for agent in get_all_agents()
      if agent.status not in _INACTIVE_STATUSES
    }
    active_launch_names = get_active_launch_agent_names()

    for name in sorted(requested_names & active_registered_names):
        issues.append(f"Имя агента уже занято в SWARM: {name}")

    for name in sorted(requested_names & active_launch_names):
        issues.append(f"Имя агента уже используется в незавершённой launch session: {name}")

    for agent in spec.agents:
        launcher_path = get_launcher_path(agent.cli, spec.approval_mode)
        if not launcher_path.exists():
            issues.append(f"Не найден launcher: {launcher_path}")

        cli_binary = _find_cli_binary(agent.cli)
        if cli_binary is None:
            if agent.cli == "opencode":
                issues.append("Не найден OpenCode CLI. Выполните repair flow: npm install -g opencode-ai")
            else:
                issues.append(f"Не найден исполняемый файл CLI для '{agent.cli}' в PATH")

    return issues

"""Генератор bootstrap prompt для терминальных агентов."""

from __future__ import annotations

from pathlib import Path


def build_bootstrap_prompt(cli_type: str, agent_name: str, agent_role: str, working_directory: Path) -> str:
    """Собирает короткий директивный prompt для авто-регистрации агента."""

    skill_path = f".{cli_type}/skills/swarm-agent/SKILL.md"
    return (
        "Ты рабочий агент SWARM.\n\n"
        f"Твой тип CLI: {cli_type}\n"
        f"Твоё имя в SWARM: {agent_name}\n"
        f"Твоя роль в SWARM: {agent_role}\n\n"
        "Рабочая директория:\n"
        f"{working_directory}\n\n"
        "Сначала прочитай:\n"
        f"{skill_path}\n\n"
        "Имя и роль уже согласованы с пользователем через оркестратора.\n"
        "Не задавай повторных вопросов про имя и роль.\n\n"
        "Зарегистрируйся:\n"
        f"swarm join --cli {cli_type} --name {agent_name} --role {agent_role}\n\n"
        "После регистрации СРАЗУ начинай работать.\n"
        f"Выполняй цикл: swarm next --agent {agent_name} → swarm lock → правки → swarm unlock → swarm done.\n"
        "Работай пока не закончатся все доступные тебе задачи.\n"
        "Когда swarm next вернёт 'нет задач' — остановись и жди."
    )

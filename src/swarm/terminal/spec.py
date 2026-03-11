"""Валидация и загрузка launch spec для swarm terminal."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..db import validate_agent_name
from ..utils import CLI_TYPES, VALID_ROLES

SPECS_DIR = Path(".swarm") / "specs"

ALLOWED_LAYOUTS = {"single", "mixed", "multi-window"}
ALLOWED_APPROVAL_MODES = {"safe", "yolo"}
# Используем общий источник ролей из utils
ALLOWED_ROLES = set(VALID_ROLES)


@dataclass
class LayoutSpec:
    """Описание layout для запуска терминалов."""

    mode: str
    max_panes_per_window: int = 4


@dataclass
class LaunchAgentSpec:
    """Описание одного агента в launch spec."""

    cli: str
    name: str
    role: str
    window: int | None = None
    pane: int | None = None


@dataclass
class LaunchSpec:
    """Полное описание запуска терминальной сессии."""

    version: int
    working_directory: str
    approval_mode: str
    layout: LayoutSpec
    agents: list[LaunchAgentSpec]


def _validate_spec(data: dict) -> None:
    if data.get("version") != 1:
        raise ValueError("Поддерживается только launch spec version=1")

    workdir = data.get("working_directory")
    if not isinstance(workdir, str) or not workdir.strip():
        raise ValueError("Поле working_directory обязательно и должно быть непустой строкой")

    approval_mode = data.get("approval_mode")
    if approval_mode not in ALLOWED_APPROVAL_MODES:
        raise ValueError("approval_mode должен быть 'safe' или 'yolo'")

    layout_data = data.get("layout")
    if not isinstance(layout_data, dict):
        raise ValueError("Поле layout обязательно и должно быть объектом")

    mode = layout_data.get("mode")
    if mode not in ALLOWED_LAYOUTS:
        raise ValueError("layout.mode должен быть одним из: single, mixed, multi-window")

    max_panes = layout_data.get("max_panes_per_window", 4)
    if not isinstance(max_panes, int) or max_panes < 1:
        raise ValueError("layout.max_panes_per_window должен быть положительным целым")

    agents_data = data.get("agents")
    if not isinstance(agents_data, list) or not agents_data:
        raise ValueError("Поле agents обязательно и должно быть непустым массивом")

    if len(agents_data) > 8:
        raise ValueError("За один запуск поддерживается максимум 8 агентов")

    if mode == "single" and len(agents_data) != 1:
        raise ValueError("layout=single допускает ровно одного агента")

    names: set[str] = set()
    for idx, agent in enumerate(agents_data, start=1):
        if not isinstance(agent, dict):
            raise ValueError(f"agents[{idx}] должен быть объектом")

        cli = agent.get("cli")
        name = agent.get("name")
        role = agent.get("role")

        if cli not in CLI_TYPES:
            raise ValueError(f"agents[{idx}].cli должен быть одним из: {', '.join(CLI_TYPES)}")

        if not isinstance(name, str):
            raise ValueError(f"agents[{idx}].name должен быть строкой")
        validate_agent_name(name)

        if name in names:
            raise ValueError(f"Имя агента '{name}' дублируется в launch spec")
        names.add(name)

        if role not in ALLOWED_ROLES:
            raise ValueError(f"agents[{idx}].role должен быть одним из: architect, developer, tester, devops")


def save_launch_spec(spec: LaunchSpec, path: Path) -> None:
    """Сохраняет launch spec в JSON-файл."""

    data = {
        "version": spec.version,
        "working_directory": spec.working_directory,
        "approval_mode": spec.approval_mode,
        "layout": {
            "mode": spec.layout.mode,
            "max_panes_per_window": spec.layout.max_panes_per_window,
        },
        "agents": [
            {
                "cli": a.cli,
                "name": a.name,
                "role": a.role,
                **({"window": a.window} if a.window is not None else {}),
                **({"pane": a.pane} if a.pane is not None else {}),
            }
            for a in spec.agents
        ],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_launch_spec(spec_path: Path) -> LaunchSpec:
    """Загружает и валидирует launch spec из JSON-файла."""

    if not spec_path.exists():
        raise ValueError(f"Файл spec не найден: {spec_path}")

    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некорректный JSON в spec: {exc}") from exc

    _validate_spec(data)

    layout = LayoutSpec(
        mode=data["layout"]["mode"],
        max_panes_per_window=data["layout"].get("max_panes_per_window", 4),
    )

    agents = [
        LaunchAgentSpec(
            cli=a["cli"],
            name=a["name"],
            role=a["role"],
            window=a.get("window"),
            pane=a.get("pane"),
        )
        for a in data["agents"]
    ]

    return LaunchSpec(
        version=data["version"],
        working_directory=data["working_directory"],
        approval_mode=data["approval_mode"],
        layout=layout,
        agents=agents,
    )

"""Построение и запуск layout-режимов Windows Terminal."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .launcher_registry import get_launcher_path
from .spec import LaunchAgentSpec, LaunchSpec


@dataclass
class LaunchResult:
  """Результат запуска отдельного процесса wt."""

  started: bool
  pid: int | None
  error: str | None = None


def _pane_command(
  working_directory: str,
  launcher_path: Path,
  prompt: str,
  session_id: str | None = None,
  agent_name: str | None = None,
) -> list[str]:
  args = [
    "-d",
    working_directory,
    "powershell",
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    str(launcher_path),
    "-Prompt",
    prompt,
  ]
  if session_id:
    args.extend(["-SessionId", session_id])
  if agent_name:
    args.extend(["-AgentName", agent_name])
  return args


def _build_mixed_window_args(
  working_directory: str,
  chunk: list[LaunchAgentSpec],
  approval_mode: str,
  prompt_map: dict[str, str],
  session_id: str | None = None,
) -> list[str]:
  first = chunk[0]
  args: list[str] = _pane_command(
    working_directory,
    get_launcher_path(first.cli, approval_mode),
    prompt_map[first.name],
    session_id=session_id,
    agent_name=first.name,
  )

  for idx, agent in enumerate(chunk[1:], start=2):
    args.append(";")
    if idx == 2:
      args.extend(["split-pane", "-V"])
    elif idx == 3:
      args.extend(["move-focus", "--direction", "left", ";", "split-pane", "-H"])
    elif idx == 4:
      args.extend(["move-focus", "--direction", "right", ";", "split-pane", "-H"])
    else:
      args.extend(["split-pane", "-V"])
    args.extend(
      _pane_command(
        working_directory,
        get_launcher_path(agent.cli, approval_mode),
        prompt_map[agent.name],
        session_id=session_id,
        agent_name=agent.name,
      )
    )
  return args


def _start_wt_process(args: list[str], working_directory: str) -> LaunchResult:
  try:
    proc = subprocess.Popen(["wt", *args], cwd=working_directory)
    return LaunchResult(started=True, pid=proc.pid)
  except Exception as exc:
    return LaunchResult(started=False, pid=None, error=str(exc))


def _agent_sort_key(agent: LaunchAgentSpec, fallback_index: int) -> tuple[int, int]:
  window = agent.window if agent.window is not None else 1
  pane = agent.pane if agent.pane is not None else fallback_index
  return window, pane


def _chunks(items: list[LaunchAgentSpec], chunk_size: int) -> list[list[LaunchAgentSpec]]:
  return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def launch_layout(
  spec: LaunchSpec,
  prompt_map: dict[str, str],
  session_id: str | None = None,
) -> dict[str, LaunchResult]:
  """Запускает агентов в wt согласно layout и возвращает результат по имени агента."""

  results: dict[str, LaunchResult] = {}
  mode = spec.layout.mode
  max_panes = max(1, spec.layout.max_panes_per_window)

  if mode == "single":
    agent = spec.agents[0]
    args = _pane_command(
      spec.working_directory,
      get_launcher_path(agent.cli, spec.approval_mode),
      prompt_map[agent.name],
      session_id=session_id,
      agent_name=agent.name,
    )
    result = _start_wt_process(args, spec.working_directory)
    results[agent.name] = result
    return results

  indexed = list(enumerate(spec.agents, start=1))
  ordered_agents = [agent for _, agent in sorted(indexed, key=lambda pair: _agent_sort_key(pair[1], pair[0]))]

  if mode == "multi-window":
    windows: dict[int, list[LaunchAgentSpec]] = {}
    for fallback_idx, agent in enumerate(ordered_agents, start=1):
      window = agent.window if agent.window is not None else fallback_idx
      windows.setdefault(window, []).append(agent)

    for window_agents in windows.values():
      ordered_window_agents = sorted(
        window_agents,
        key=lambda a: (a.pane if a.pane is not None else 10_000, a.name),
      )
      for chunk in _chunks(ordered_window_agents, max_panes):
        args = _build_mixed_window_args(
          spec.working_directory, chunk, spec.approval_mode, prompt_map, session_id=session_id,
        )
        result = _start_wt_process(args, spec.working_directory)
        for agent in chunk:
          results[agent.name] = result
    return results

  # mode == mixed
  for i in range(0, len(ordered_agents), max_panes):
    chunk = ordered_agents[i : i + max_panes]
    args = _build_mixed_window_args(
      spec.working_directory, chunk, spec.approval_mode, prompt_map, session_id=session_id,
    )
    result = _start_wt_process(args, spec.working_directory)
    for agent in chunk:
      results[agent.name] = result
  return results

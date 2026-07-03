---
name: terminal
description: "Skill for the Terminal area of SWARM. 12 symbols across 5 files."
---

# Terminal

12 symbols | 5 files | Cohesion: 82%

## When to Use

- Working with code in `src/`
- Understanding how launch_layout, get_launchers_dir, get_launcher_path work
- Modifying terminal-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/swarm/terminal/layouts.py` | _pane_command, _build_mixed_window_args, _start_wt_process, _agent_sort_key, _chunks (+1) |
| `src/swarm/terminal/launcher_registry.py` | get_launchers_dir, get_launcher_path |
| `src/swarm/terminal/preflight.py` | _find_cli_binary, run_preflight |
| `tests/test_db.py` | test_active_launch_agent_names |
| `src/swarm/db.py` | get_active_launch_agent_names |

## Entry Points

Start here when exploring this area:

- **`launch_layout`** (Function) — `src/swarm/terminal/layouts.py:103`
- **`get_launchers_dir`** (Function) — `src/swarm/terminal/launcher_registry.py:7`
- **`get_launcher_path`** (Function) — `src/swarm/terminal/launcher_registry.py:13`
- **`test_active_launch_agent_names`** (Function) — `tests/test_db.py:830`
- **`get_active_launch_agent_names`** (Function) — `src/swarm/db.py:894`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `launch_layout` | Function | `src/swarm/terminal/layouts.py` | 103 |
| `get_launchers_dir` | Function | `src/swarm/terminal/launcher_registry.py` | 7 |
| `get_launcher_path` | Function | `src/swarm/terminal/launcher_registry.py` | 13 |
| `test_active_launch_agent_names` | Function | `tests/test_db.py` | 830 |
| `get_active_launch_agent_names` | Function | `src/swarm/db.py` | 894 |
| `run_preflight` | Function | `src/swarm/terminal/preflight.py` | 32 |
| `_pane_command` | Function | `src/swarm/terminal/layouts.py` | 21 |
| `_build_mixed_window_args` | Function | `src/swarm/terminal/layouts.py` | 47 |
| `_start_wt_process` | Function | `src/swarm/terminal/layouts.py` | 85 |
| `_agent_sort_key` | Function | `src/swarm/terminal/layouts.py` | 93 |
| `_chunks` | Function | `src/swarm/terminal/layouts.py` | 99 |
| `_find_cli_binary` | Function | `src/swarm/terminal/preflight.py` | 16 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Launch_command → Get_launchers_dir` | cross_community | 4 |
| `Launch_command → Get_all_agents` | cross_community | 3 |
| `Launch_command → Get_active_launch_agent_names` | cross_community | 3 |
| `Launch_command → _find_cli_binary` | cross_community | 3 |
| `Launch_layout → Get_launchers_dir` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 1 calls |

## How to Explore

1. `gitnexus_context({name: "launch_layout"})` — see callers and callees
2. `gitnexus_query({query: "terminal"})` — find related execution flows
3. Read key files listed above for implementation details

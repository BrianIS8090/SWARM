---
name: swarm
description: "Skill for the Swarm area of SWARM. 27 symbols across 7 files."
---

# Swarm

27 symbols | 7 files | Cohesion: 80%

## When to Use

- Working with code in `src/`
- Understanding how test_add_launch_session_agent_and_status_update, test_reconcile_marks_registered_agents, ensure_terminal_schema work
- Modifying swarm-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/swarm/db.py` | ensure_terminal_schema, add_launch_session_agent, get_launch_session_agents, reconcile_launch_session, create_launch_session (+6) |
| `tests/test_db.py` | test_add_launch_session_agent_and_status_update, test_reconcile_marks_registered_agents, test_create_and_get_launch_session, test_update_launch_session_status_and_list, test_self_dependency_detected |
| `src/swarm/commands/terminal.py` | status_command, reconcile_command, stop_command |
| `src/swarm/models.py` | _safe_enum, _parse_dt, from_row |
| `tests/test_models.py` | test_valid_value, test_unknown_value_returns_unknown |
| `src/swarm/utils.py` | _configure_stdio_for_unicode, create_console |
| `src/swarm/commands/tui.py` | run_tui |

## Entry Points

Start here when exploring this area:

- **`test_add_launch_session_agent_and_status_update`** (Function) — `tests/test_db.py:765`
- **`test_reconcile_marks_registered_agents`** (Function) — `tests/test_db.py:799`
- **`ensure_terminal_schema`** (Function) — `src/swarm/db.py:188`
- **`add_launch_session_agent`** (Function) — `src/swarm/db.py:818`
- **`get_launch_session_agents`** (Function) — `src/swarm/db.py:856`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_add_launch_session_agent_and_status_update` | Function | `tests/test_db.py` | 765 |
| `test_reconcile_marks_registered_agents` | Function | `tests/test_db.py` | 799 |
| `ensure_terminal_schema` | Function | `src/swarm/db.py` | 188 |
| `add_launch_session_agent` | Function | `src/swarm/db.py` | 818 |
| `get_launch_session_agents` | Function | `src/swarm/db.py` | 856 |
| `reconcile_launch_session` | Function | `src/swarm/db.py` | 914 |
| `status_command` | Function | `src/swarm/commands/terminal.py` | 273 |
| `reconcile_command` | Function | `src/swarm/commands/terminal.py` | 357 |
| `test_create_and_get_launch_session` | Function | `tests/test_db.py` | 746 |
| `test_update_launch_session_status_and_list` | Function | `tests/test_db.py` | 874 |
| `create_launch_session` | Function | `src/swarm/db.py` | 756 |
| `get_launch_session` | Function | `src/swarm/db.py` | 788 |
| `get_launch_sessions` | Function | `src/swarm/db.py` | 797 |
| `update_launch_session_status` | Function | `src/swarm/db.py` | 811 |
| `stop_command` | Function | `src/swarm/commands/terminal.py` | 305 |
| `test_valid_value` | Function | `tests/test_models.py` | 132 |
| `test_unknown_value_returns_unknown` | Function | `tests/test_models.py` | 136 |
| `from_row` | Function | `src/swarm/models.py` | 118 |
| `test_self_dependency_detected` | Function | `tests/test_db.py` | 534 |
| `get_db_path` | Function | `src/swarm/db.py` | 154 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Reconcile_command → Get_launch_session` | cross_community | 3 |
| `Reconcile_command → Get_launch_session_agents` | intra_community | 3 |
| `Add_command → _has_dependency_cycle` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 3 calls |
| Tests | 2 calls |

## How to Explore

1. `gitnexus_context({name: "test_add_launch_session_agent_and_status_update"})` — see callers and callees
2. `gitnexus_query({query: "swarm"})` — find related execution flows
3. Read key files listed above for implementation details

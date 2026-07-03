---
name: commands
description: "Skill for the Commands area of SWARM. 59 symbols across 14 files."
---

# Commands

59 symbols | 14 files | Cohesion: 69%

## When to Use

- Working with code in `src/`
- Understanding how test_get_all_agents, test_force_all_removes_all_agents, test_register_multiple_agents work
- Modifying commands-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/swarm/commands/tui.py` | _fmt_heartbeat, _fmt_dt, _refresh_agents_table, _format_agent_detail, _format_task_detail (+12) |
| `src/swarm/commands/path_cmd.py` | _get_user_scripts_dir, _split_path_entries, _contains_path_entry, _read_user_path_windows, _write_user_path_windows (+2) |
| `src/swarm/db.py` | get_all_agents, get_recent_events, create_task, is_process_alive, cleanup_dead_agents (+1) |
| `src/swarm/commands/monitor.py` | create_agents_panel, create_tasks_panel, create_locks_panel, create_activity_panel, create_dashboard (+1) |
| `src/swarm/commands/task.py` | _ensure_leader_context, add_command, list_command, close_command, reset_command (+1) |
| `src/swarm/commands/agent.py` | agents_command, next_command, status_command, heartbeat_command |
| `src/swarm/commands/terminal.py` | _print_launch_plan, _auto_layout_mode, launch_command, _print_excluded_command |
| `tests/test_db.py` | test_get_all_agents, test_force_all_removes_all_agents |
| `tests/test_agents.py` | test_register_multiple_agents, test_update_heartbeat |
| `src/swarm/commands/logs.py` | logs_command |

## Entry Points

Start here when exploring this area:

- **`test_get_all_agents`** (Function) — `tests/test_db.py:113`
- **`test_force_all_removes_all_agents`** (Function) — `tests/test_db.py:931`
- **`test_register_multiple_agents`** (Function) — `tests/test_agents.py:34`
- **`get_all_agents`** (Function) — `src/swarm/db.py:263`
- **`get_recent_events`** (Function) — `src/swarm/db.py:993`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_get_all_agents` | Function | `tests/test_db.py` | 113 |
| `test_force_all_removes_all_agents` | Function | `tests/test_db.py` | 931 |
| `test_register_multiple_agents` | Function | `tests/test_agents.py` | 34 |
| `get_all_agents` | Function | `src/swarm/db.py` | 263 |
| `get_recent_events` | Function | `src/swarm/db.py` | 993 |
| `create_agents_panel` | Function | `src/swarm/commands/monitor.py` | 33 |
| `create_tasks_panel` | Function | `src/swarm/commands/monitor.py` | 104 |
| `create_locks_panel` | Function | `src/swarm/commands/monitor.py` | 204 |
| `create_activity_panel` | Function | `src/swarm/commands/monitor.py` | 256 |
| `create_dashboard` | Function | `src/swarm/commands/monitor.py` | 313 |
| `monitor_command` | Function | `src/swarm/commands/monitor.py` | 336 |
| `logs_command` | Function | `src/swarm/commands/logs.py` | 16 |
| `check_db` | Function | `src/swarm/utils.py` | 53 |
| `create_task` | Function | `src/swarm/db.py` | 392 |
| `add_command` | Function | `src/swarm/commands/task.py` | 47 |
| `list_command` | Function | `src/swarm/commands/task.py` | 112 |
| `close_command` | Function | `src/swarm/commands/task.py` | 226 |
| `reset_command` | Function | `src/swarm/commands/task.py` | 270 |
| `assign_command` | Function | `src/swarm/commands/task.py` | 311 |
| `start_command` | Function | `src/swarm/commands/start.py` | 17 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `On_mount → Is_process_alive` | cross_community | 5 |
| `Action_refresh → Is_process_alive` | cross_community | 5 |
| `Action_toggle_done → Is_process_alive` | cross_community | 5 |
| `Launch_command → Validate_agent_name` | cross_community | 4 |
| `Launch_command → Get_launchers_dir` | cross_community | 4 |
| `Add_command → Get_agent_by_session` | cross_community | 4 |
| `Close_command → Get_agent_by_session` | cross_community | 4 |
| `Reset_command → Get_agent_by_session` | cross_community | 4 |
| `Next_command → Get_agent_by_session` | cross_community | 4 |
| `On_data_table_row_highlighted → Is_process_alive` | intra_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 18 calls |
| Swarm | 5 calls |
| Terminal | 2 calls |

## How to Explore

1. `gitnexus_context({name: "test_get_all_agents"})` — see callers and callees
2. `gitnexus_query({query: "commands"})` — find related execution flows
3. Read key files listed above for implementation details

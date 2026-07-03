---
name: tests
description: "Skill for the Tests area of SWARM. 166 symbols across 18 files."
---

# Tests

166 symbols | 18 files | Cohesion: 68%

## When to Use

- Working with code in `tests/`
- Understanding how test_complete_releases_locks, test_reset_releases_locks, test_unlock_foreign_lock_denied work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/test_db.py` | test_lock_file, test_lock_already_locked_file, test_unlock_file, test_force_unlock, test_agent_cannot_lock_two_files_at_once (+39) |
| `tests/test_spec.py` | _make_valid_spec, test_valid_spec_passes, test_valid_multi_window_layout, test_all_roles, test_invalid_version (+30) |
| `src/swarm/db.py` | try_lock_file, get_file_lock, get_all_locks, get_agent_lock, unlock_task_files (+16) |
| `tests/test_models.py` | _agent_row, _task_row, _launch_session_row, test_valid_status, test_unknown_status (+11) |
| `tests/test_tasks.py` | test_complete_releases_locks, test_reset_releases_locks, test_claim_task, test_claim_no_tasks, test_claim_respects_priority (+10) |
| `tests/test_edge_cases.py` | test_unlock_foreign_lock_denied, test_lock_same_file_twice_by_same_agent_is_idempotent, test_lock_different_file_while_holding_lock, test_assign_done_task_returns_false, test_assign_in_progress_task_returns_false (+1) |
| `tests/test_utils.py` | test_returns_string, test_cached_second_call, test_file_not_found_returns_unknown, test_invalid_json_returns_unknown, test_missing_version_key_returns_unknown |
| `src/swarm/terminal/spec.py` | _validate_spec, save_launch_spec, load_launch_spec |
| `src/swarm/commands/init.py` | get_orchestrator_skill_template, get_skill_template, init_command |
| `tests/test_agents.py` | test_update_status, test_get_current_agent, test_get_current_agent_no_session |

## Entry Points

Start here when exploring this area:

- **`test_complete_releases_locks`** (Function) — `tests/test_tasks.py:149`
- **`test_reset_releases_locks`** (Function) — `tests/test_tasks.py:224`
- **`test_unlock_foreign_lock_denied`** (Function) — `tests/test_edge_cases.py:31`
- **`test_lock_same_file_twice_by_same_agent_is_idempotent`** (Function) — `tests/test_edge_cases.py:49`
- **`test_lock_different_file_while_holding_lock`** (Function) — `tests/test_edge_cases.py:65`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_complete_releases_locks` | Function | `tests/test_tasks.py` | 149 |
| `test_reset_releases_locks` | Function | `tests/test_tasks.py` | 224 |
| `test_unlock_foreign_lock_denied` | Function | `tests/test_edge_cases.py` | 31 |
| `test_lock_same_file_twice_by_same_agent_is_idempotent` | Function | `tests/test_edge_cases.py` | 49 |
| `test_lock_different_file_while_holding_lock` | Function | `tests/test_edge_cases.py` | 65 |
| `test_lock_file` | Function | `tests/test_db.py` | 178 |
| `test_lock_already_locked_file` | Function | `tests/test_db.py` | 192 |
| `test_unlock_file` | Function | `tests/test_db.py` | 208 |
| `test_force_unlock` | Function | `tests/test_db.py` | 217 |
| `test_agent_cannot_lock_two_files_at_once` | Function | `tests/test_db.py` | 230 |
| `test_force_close_releases_locks` | Function | `tests/test_db.py` | 330 |
| `test_cleanup_releases_tasks_and_locks` | Function | `tests/test_db.py` | 395 |
| `test_empty_locks` | Function | `tests/test_db.py` | 456 |
| `test_returns_all_locks` | Function | `tests/test_db.py` | 460 |
| `test_unlock_removes_task_locks` | Function | `tests/test_db.py` | 480 |
| `test_unlock_nonexistent_task` | Function | `tests/test_db.py` | 491 |
| `test_force_all_deletes_locks` | Function | `tests/test_db.py` | 914 |
| `try_lock_file` | Function | `src/swarm/db.py` | 660 |
| `get_file_lock` | Function | `src/swarm/db.py` | 703 |
| `get_all_locks` | Function | `src/swarm/db.py` | 713 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Launch_command → Validate_agent_name` | cross_community | 4 |
| `Lock_command → Get_agent_by_session` | cross_community | 4 |
| `Unlock_command → Get_agent_by_session` | cross_community | 4 |
| `Add_command → Get_agent_by_session` | cross_community | 4 |
| `Close_command → Get_agent_by_session` | cross_community | 4 |
| `Reset_command → Get_agent_by_session` | cross_community | 4 |
| `Next_command → Get_agent_by_session` | cross_community | 4 |
| `Monitor_command → Get_all_locks` | cross_community | 4 |
| `Done_command → Get_agent_by_session` | cross_community | 4 |
| `Status_command → Get_agent_by_session` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 8 calls |

## How to Explore

1. `gitnexus_context({name: "test_complete_releases_locks"})` — see callers and callees
2. `gitnexus_query({query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details

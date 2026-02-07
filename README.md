# SWARM — Multi-Agent Orchestration System

SWARM is a local system for coordinating multiple LLM agents (Claude, Codex, Gemini, OpenCode, Qwen) working in parallel on a shared codebase.

<img width="2529" height="1323" alt="Screenshot 2026-02-06 134233" src="https://github.com/user-attachments/assets/0d05ba34-7886-459f-844b-d2132f9f832c" />

<img width="2330" height="1343" alt="Screenshot 2026-02-06 134238" src="https://github.com/user-attachments/assets/4780894c-ae0e-4302-9efa-831ff8f1802d" />


## Features

- **Unified CLI interface** (`swarm`) for managing agents and tasks
- **Task distribution** with priorities and filtering by role / name / CLI type
- **File locking** to prevent conflicts during parallel editing
- **Live monitor** for real-time status tracking
- **Direct task assignment** to specific agents
- **Fully local operation** — no cloud dependencies

## Quick Start

### 1. Installation

```bash
# From the SWARM directory
pip install -e .

2. Project Initialization

Go to your project directory and run:

cd your-project
swarm init

This will create:

swarm.db — database for tasks and agents

SKILLS.md — instructions for LLM agents


3. Creating Tasks

# Simple task
swarm task add --desc "Implement authentication" --priority 1

# Task for a specific role
swarm task add --desc "Design API" --priority 1 --role architect

# Task with dependency (will run after task #1)
swarm task add --desc "Write tests" --priority 2 --depends-on 1

Priorities: 1 (highest) — 5 (lowest)

Roles: architect, developer, tester, devops

CLI types: claude, codex, gemini, opencode, qwen

4. Launching Agents

Open a new terminal for each agent:

# Terminal 1: launch Claude CLI
claude

# In Claude, say:
# "Read SKILLS.md and register via swarm join"

The agent will execute:

swarm join
# It will enter: CLI type, name, role

⚠ IMPORTANT: Agents must use the --agent parameter

After registration, the agent must remember its name and use it in all commands:

# Registration
swarm join --cli codex --name worker1 --role developer

# All subsequent commands — with --agent
swarm next --agent worker1
swarm lock file.py --agent worker1
swarm done --summary "..." --agent worker1

This allows running multiple agents of the same type (e.g., 5 Codex agents) without conflicts.

Repeat this for each agent in a separate terminal.

5. Starting the Monitor

In a separate terminal:

swarm monitor

You will see a live dashboard with 4 panels:

Agents — status of each agent

Tasks — task queue

Locks — which files are locked

Activity — recent events


6. Starting Work

In each agent’s terminal, tell the agent in plain text:

> "Start working. Run swarm next --agent your-name to get a task."



The agent will follow this loop:

1. Get a task (swarm next --agent name)


2. Lock files (swarm lock file --agent name)


3. Perform the work


4. Complete the task (swarm done --agent name)


5. Take the next task



Important: Agents are LLMs in separate terminals. They do not automatically “listen” to the database. You must manually tell each agent to start working.


---

Commands

Leader (Operator) Commands

Command	Description

swarm init	Initialize the SWARM environment
swarm task add	Create a task
swarm task list	Show task list
swarm task assign <ID> --agent <name>	Assign a task to an agent
swarm task close <ID>	Force-close a task
swarm agents	Show agent list
swarm agents --cleanup	Remove inactive agents
swarm monitor	Start live dashboard
swarm tui	TUI monitor with scrolling
swarm logs	Show event log
swarm unlock --force	Force-remove a lock


Agent Commands

All agent commands use the --agent <name> parameter:

Command	Description

swarm join	Register an agent
swarm next --agent name	Get the next task
swarm lock <files> --agent name	Lock files
swarm done --agent name	Complete a task
swarm status --agent name	Show agent status
swarm unlock --agent name	Release own locks


Agent Roles

architect — architecture and design

developer — feature development

tester — testing

devops — infrastructure and deployment


CLI Types

claude — Claude Code

codex — OpenAI Codex CLI

gemini — Gemini CLI

opencode — OpenCode CLI

qwen — Qwen CLI


Project Structure

SWARM/
├── src/swarm/          # Source code
├── tests/              # Tests
├── memory-bank/        # Project context
├── .claude/            # Skills for Claude
├── .codex/             # Skills for Codex
├── .gemini/            # Skills for Gemini
├── .opencode/          # Skills for OpenCode
├── .qwen/              # Skills for Qwen
├── USER_GUIDE.md       # User guide
└── pyproject.toml      # Project configuration

License

MIT
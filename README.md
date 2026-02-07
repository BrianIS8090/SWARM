
SWARM — Multi-Agent Orchestration System
SWARM is a local system for coordinating multiple LLM agents (Claude, Codex, Gemini, OpenCode, Qwen) working in parallel on a shared codebase.
<img width="2529" height="1323" alt="Screen Shot 2026-02-06 134233" src="https://github.com/user-attachments/assets/0d05ba34-7886-459f-844b-d2132f9f832c" />
<img width="2330" height="1343" alt="Screen Shot 2026-02-06 134238" src="https://github.com/user-attachments/assets/4780894c-ae0e-4302-9efa-831ff8f1802d" />
Features
 * Unified CLI Interface (swarm) for managing agents and tasks.
 * Task Distribution with priorities and filtering by role/name/CLI type.
 * File Locking to prevent conflicts during parallel editing.
 * Live Monitor for real-time status tracking.
 * Task Assignment to specific agents.
 * Fully Local Operation — no cloud dependencies.
Quick Start
1. Installation
# From the SWARM directory
pip install -e .

2. Project Initialization
Navigate to your project folder and run:
cd your-project
swarm init

This creates:
 * swarm.db — database for tasks and agents.
 * SKILLS.md — instructions/skills for the LLM agents.
3. Creating Tasks
# Simple task
swarm task add --desc "Implement authorization" --priority 1

# Task for a specific role
swarm task add --desc "Design API" --priority 1 --role architect

# Task with a dependency (runs only after task #1 is complete)
swarm task add --desc "Write tests" --priority 2 --depends-on 1

Priorities: 1 (Highest) — 5 (Lowest)
Roles: architect, developer, tester, devops
CLI Types: claude, codex, gemini, opencode, qwen
4. Launching Agents
Open a new terminal window for each agent you want to run:
# Terminal 1: Launch Claude CLI
claude

# Inside Claude, say:
# "Read SKILLS.md and register using swarm join"

The agent will execute:
swarm join
# It will enter: CLI type, name, role

⚠ IMPORTANT: Agents must use the --agent parameter
After registration, the agent must remember its name and use it in all subsequent commands:
# Registration
swarm join --cli codex --name worker1 --role developer

# All subsequent commands — must include --agent
swarm next --agent worker1
swarm lock file.py --agent worker1
swarm done --summary "..." --agent worker1

This allows you to run multiple agents of the same type (e.g., 5 Codex instances) without conflicts.
Repeat this process for each agent in a separate terminal.
5. Launching the Monitor
In a separate terminal:
swarm monitor

You will see a live dashboard with 4 panels:
 * Agents — status of each agent.
 * Tasks — the task queue.
 * Locks — currently locked files.
 * Activity — recent events log.
6. Starting Work
In each agent's terminal, tell them via text prompt:
> "Start working. Run swarm next --agent your-name to get a task."
> 
The agent will enter a loop:
 * Get a task (swarm next --agent name)
 * Lock files (swarm lock file --agent name)
 * Perform the work
 * Complete the task (swarm done --agent name)
 * Pick up the next task
Note: Agents are LLMs running in separate terminals. They do not "listen" to the database automatically. You must manually prompt each agent to begin the workflow.
Commands
Leader (Operator) Commands
| Command | Description |
|---|---|
| swarm init | Initialize the SWARM environment |
| swarm task add | Create a new task |
| swarm task list | Show the list of tasks |
| swarm task assign <ID> --agent <name> | Assign a task to a specific agent |
| swarm task close <ID> | Force close a task |
| swarm agents | Show the list of agents |
| swarm agents --cleanup | Remove inactive agents |
| swarm monitor | Launch the live dashboard |
| swarm tui | Launch TUI monitor with scrolling |
| swarm logs | Show the event log |
| swarm unlock --force | Force release a file lock |
Agent Commands
All agent commands require the --agent <name> parameter:
| Command | Description |
|---|---|
| swarm join | Register the agent |
| swarm next --agent name | Get the next available task |
| swarm lock <files> --agent name | Lock files for editing |
| swarm done --agent name | Complete the current task |
| swarm status --agent name | Show agent status |
| swarm unlock --agent name | Release own locks |
Agent Roles
 * architect — Architecture and design
 * developer — Functionality development
 * tester — Testing and QA
 * devops — Infrastructure and deployment
Supported CLI Types
 * claude — Claude Code
 * codex — OpenAI Codex CLI
 * gemini — Gemini CLI
 * opencode — OpenCode CLI
 * qwen — Qwen CLI
Project Structure
SWARM/
├── src/swarm/          # Source code
├── tests/              # Tests
├── memory-bank/        # Project context
├── .claude/            # Skills/Instructions for Claude
├── .codex/             # Skills/Instructions for Codex
├── .gemini/            # Skills/Instructions for Gemini
├── .opencode/          # Skills/Instructions for OpenCode
├── .qwen/              # Skills/Instructions for Qwen
├── USER_GUIDE.md       # User Guide
└── pyproject.toml      # Project configuration

License
MIT

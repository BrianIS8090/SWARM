"""
TUI-монитор SWARM на базе Textual.

Презентабельный интерфейс с 6 вкладками и детальными панелями.
"""

from datetime import UTC, datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import (
  DataTable,
  Footer,
  Header,
  Label,
  Static,
  TabbedContent,
  TabPane,
)

from ..db import (
  find_db_path,
  get_all_agents,
  get_all_locks,
  get_all_tasks,
  get_recent_events,
  is_process_alive,
)
from ..models import Agent, AgentStatus, EventType, FileLock, Task, TaskLogEntry, TaskStatus
from ..utils import create_console, get_version

from rich.markup import escape as _esc

# ── Иконки статусов ──────────────────────────────────────────────

AGENT_STATUS_ICONS = {
  AgentStatus.IDLE: ("○", "dim"),
  AgentStatus.WORKING: ("●", "green"),
  AgentStatus.WAITING: ("◐", "yellow"),
  AgentStatus.DONE: ("✓", "blue"),
}

TASK_STATUS_ICONS = {
  TaskStatus.PENDING: ("⏳", "yellow"),
  TaskStatus.IN_PROGRESS: ("▶", "green"),
  TaskStatus.DONE: ("✓", "dim"),
  TaskStatus.BLOCKED: ("✗", "red"),
  TaskStatus.FAILED: ("✗", "red"),
}

EVENT_ICONS = {
  EventType.TASK_STARTED: ("▶", "green"),
  EventType.TASK_DONE: ("✓", "blue"),
  EventType.TASK_CREATED: ("＋", "cyan"),
  EventType.TASK_ASSIGNED: ("→", "cyan"),
  EventType.TASK_FORCE_CLOSED: ("✗", "red"),
  EventType.FILE_LOCKED: ("🔒", "yellow"),
  EventType.FILE_UNLOCKED: ("🔓", "dim"),
  EventType.WAITING_FOR_LOCK: ("⏳", "red"),
  EventType.ERROR: ("✗", "red"),
  EventType.AGENT_REGISTERED: ("＋", "cyan"),
  EventType.AGENT_STARTED: ("▶", "green"),
  EventType.AGENT_CLEANUP: ("✗", "dim"),
}


# ── Вспомогательные функции ──────────────────────────────────────

def _fmt_heartbeat(agent: Agent, now: datetime) -> str:
  """Форматирует heartbeat: '5с', '3м', '1ч'."""
  if not agent.last_heartbeat:
    return "-"
  secs = int((now - agent.last_heartbeat).total_seconds())
  if secs < 60:
    hb = f"{secs}с"
  elif secs < 3600:
    hb = f"{secs // 60}м"
  else:
    hb = f"{secs // 3600}ч"
  pid_alive = is_process_alive(agent.pid) if agent.pid is not None else None
  if secs > 300 and pid_alive is not True:
    return f"[red]{hb}[/red]"
  if secs > 300:
    return f"[yellow]{hb}*[/yellow]"
  return hb


def _fmt_duration_mins(minutes: int) -> str:
  """Форматирует длительность в минутах."""
  if minutes < 60:
    return f"{minutes}м"
  return f"{minutes // 60}ч {minutes % 60}м"


def _fmt_dt(dt: datetime | None) -> str:
  """Форматирует datetime для отображения."""
  if dt is None:
    return "—"
  return dt.strftime("%Y-%m-%d %H:%M")


def _progress_bar(done: int, total: int, width: int = 20) -> str:
  """Текстовый прогресс-бар: [████████░░░░] 42%."""
  if total == 0:
    return "[dim]нет задач[/dim]"
  filled = int(done / total * width)
  empty = width - filled
  pct = int(done / total * 100)
  bar = "█" * filled + "░" * empty
  return f"[green]{bar}[/green] {pct}%"


# ── StatsBar ─────────────────────────────────────────────────────

class StatsBar(Static):
  """Верхняя полоса со счётчиками и прогрессом."""

  def refresh_data(
    self,
    agents: list[Agent],
    tasks: list[Task],
    locks: list[FileLock],
  ) -> None:
    working = sum(1 for a in agents if a.status == AgentStatus.WORKING)
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    total = len(tasks)
    blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
    failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)

    # Статус БД
    db_connected = find_db_path() is not None
    db_str = "[green]● БД[/green]" if db_connected else "[red]○ БД[/red]"

    parts = [
      f"  [bold]SWARM[/bold] [dim]v{get_version()}[/dim]",
      db_str,
      f"🤖 [bold cyan]{working}[/]/{len(agents)}",
      f"📋 [bold green]{done}[/]/{total}",
    ]
    if blocked:
      parts.append(f"🚫 [bold red]{blocked}[/]")
    if failed:
      parts.append(f"✗ [bold red]{failed}[/]")
    parts.append(f"🔒 [bold yellow]{len(locks)}[/]")
    parts.append(_progress_bar(done, total, 16))

    self.update("  │  ".join(parts))


# ── Мини-панели для вкладки Обзор ────────────────────────────────

class OverviewAgentsPanel(Static):
  """Компактная таблица агентов для обзора."""

  def compose(self) -> ComposeResult:
    yield Label("[bold cyan]🤖 Агенты[/bold cyan]", classes="panel-title")
    yield DataTable(id="ov-agents-dt", cursor_type="row")

  def on_mount(self) -> None:
    table = self.query_one("#ov-agents-dt", DataTable)
    table.add_columns("", "Имя", "Роль", "Статус", "Задача")

  def refresh_data(self, agents: list[Agent]) -> None:
    table = self.query_one("#ov-agents-dt", DataTable)
    cursor_row = table.cursor_row if table.row_count > 0 else 0
    table.clear()
    for a in agents:
      icon, color = AGENT_STATUS_ICONS.get(a.status, ("?", "white"))
      task = f"#{a.current_task_id}" if a.current_task_id else "—"
      table.add_row(
        f"[{color}]{icon}[/{color}]",
        a.name,
        a.role or "—",
        f"[{color}]{a.status.value}[/{color}]",
        task,
      )
    if cursor_row < table.row_count:
      table.move_cursor(row=cursor_row)


class OverviewTasksPanel(Static):
  """Компактная таблица задач для обзора."""

  def compose(self) -> ComposeResult:
    yield Label("[bold magenta]📋 Задачи[/bold magenta]", classes="panel-title")
    yield DataTable(id="ov-tasks-dt", cursor_type="row")

  def on_mount(self) -> None:
    table = self.query_one("#ov-tasks-dt", DataTable)
    table.add_columns("", "ID", "P", "Статус", "Описание")

  def refresh_data(self, tasks: list[Task]) -> None:
    table = self.query_one("#ov-tasks-dt", DataTable)
    cursor_row = table.cursor_row if table.row_count > 0 else 0
    table.clear()
    # Обзор показывает только активные задачи
    filtered = [t for t in tasks if t.status != TaskStatus.DONE]
    for t in filtered[:30]:
      icon, color = TASK_STATUS_ICONS.get(t.status, ("?", "white"))
      desc = t.description
      if len(desc) > 28:
        desc = desc[:25] + "..."
      table.add_row(
        f"[{color}]{icon}[/{color}]",
        f"[cyan]#{t.task_id}[/cyan]",
        str(t.priority),
        f"[{color}]{t.status.value}[/{color}]",
        _esc(desc),
      )
    if cursor_row < table.row_count:
      table.move_cursor(row=cursor_row)


class OverviewLocksPanel(Static):
  """Компактная таблица блокировок для обзора."""

  def compose(self) -> ComposeResult:
    yield Label("[bold yellow]🔒 Блокировки[/bold yellow]", classes="panel-title")
    yield DataTable(id="ov-locks-dt", cursor_type="row")

  def on_mount(self) -> None:
    table = self.query_one("#ov-locks-dt", DataTable)
    table.add_columns("", "Файл", "Агент", "Время")

  def refresh_data(
    self,
    locks: list[FileLock],
    agents_map: dict[int, Agent],
  ) -> None:
    table = self.query_one("#ov-locks-dt", DataTable)
    cursor_row = table.cursor_row if table.row_count > 0 else 0
    table.clear()
    now = datetime.now(UTC).replace(tzinfo=None)
    for lock in locks:
      agent = agents_map.get(lock.locked_by)
      name = agent.name if agent else f"#{lock.locked_by}"
      path = lock.file_path
      if len(path) > 25:
        path = "…" + path[-24:]
      mins = int((now - lock.locked_at).total_seconds() / 60) if lock.locked_at else 0
      time_str = _fmt_duration_mins(mins)
      if mins > 30:
        time_str = f"[red]{time_str}[/red]"
      table.add_row("[yellow]●[/yellow]", path, name, time_str)
    if cursor_row < table.row_count:
      table.move_cursor(row=cursor_row)


class OverviewActivityPanel(Static):
  """Компактный лог активности для обзора."""

  def compose(self) -> ComposeResult:
    yield Label("[bold green]📜 Активность[/bold green]", classes="panel-title")
    yield VerticalScroll(Static("", id="ov-activity-log"), id="ov-activity-scroll")

  def refresh_data(
    self,
    events: list[TaskLogEntry],
    agents_map: dict[int, Agent],
  ) -> None:
    lines = []
    for e in events[:15]:
      time_str = e.timestamp.strftime("%H:%M:%S") if e.timestamp else "--:--:--"
      icon, color = EVENT_ICONS.get(e.event, ("•", "white"))
      agent = agents_map.get(e.agent_id) if e.agent_id else None
      agent_name = agent.name if agent else "—"
      task_str = f"[magenta]#{e.task_id}[/magenta]" if e.task_id else "   "
      msg = e.message or e.event.value
      if len(msg) > 30:
        msg = msg[:27] + "..."
      lines.append(
        f"[dim]{time_str}[/dim] [{color}]{icon}[/{color}] {task_str} "
        f"[cyan]{agent_name:8}[/cyan] {_esc(msg)}"
      )
    log = self.query_one("#ov-activity-log", Static)
    log.update("\n".join(lines) if lines else "[dim]Нет событий[/dim]")


# ── Главное приложение ────────────────────────────────────────────

class SwarmTUI(App):
  """Презентабельный TUI-монитор SWARM."""

  CSS = """
  /* ── Основа ── */
  Screen {
    background: $surface;
  }

  /* ── StatsBar ── */
  StatsBar {
    dock: top;
    height: 1;
    padding: 0 1;
    background: $boost;
    color: $text;
  }

  /* ── Табы ── */
  TabbedContent {
    height: 1fr;
  }

  TabPane {
    padding: 0 1;
  }

  /* ── Вкладка Обзор — сетка 2x2 ── */
  #overview-top, #overview-bottom {
    height: 1fr;
  }

  OverviewAgentsPanel, OverviewTasksPanel,
  OverviewLocksPanel, OverviewActivityPanel {
    width: 1fr;
    height: 1fr;
    border: round $primary-darken-2;
    margin: 0 1 0 0;
    padding: 0;
  }

  .panel-title {
    height: 1;
    padding: 0 1;
    background: $primary-darken-2;
    text-style: bold;
  }

  #ov-activity-scroll {
    height: 1fr;
  }

  #ov-activity-log {
    height: auto;
    padding: 0 1;
  }

  /* ── Таблицы ── */
  DataTable {
    height: 1fr;
  }

  DataTable > .datatable--header {
    background: $primary-darken-2;
    color: $text;
    text-style: bold;
  }

  DataTable > .datatable--cursor {
    background: $primary;
    color: $text;
  }

  DataTable > .datatable--hover {
    background: $primary-darken-1;
  }

  /* ── Detail-панели ── */
  .detail-panel {
    height: auto;
    max-height: 8;
    border-top: heavy $accent;
    padding: 0 1;
    background: $surface-darken-1;
    margin: 0;
  }

  /* ── Полноэкранные табы ── */
  .full-tab-content {
    height: 1fr;
  }

  /* ── Лог активности ── */
  #activity-scroll {
    height: 1fr;
  }

  #activity-log {
    height: auto;
    padding: 0 1;
  }
  """

  BINDINGS = [
    Binding("q", "quit", "Выход"),
    Binding("r", "refresh", "Обновить"),
    Binding("d", "toggle_dark", "Тема"),
    Binding("f", "toggle_done", "Фильтр done"),
    Binding("1", "tab_1", "Обзор"),
    Binding("2", "tab_2", "Агенты"),
    Binding("3", "tab_3", "Задачи"),
    Binding("4", "tab_4", "Все задачи"),
    Binding("5", "tab_5", "Блокировки"),
    Binding("6", "tab_6", "Активность"),
  ]

  show_done: reactive[bool] = reactive(False)
  refresh_timer: Timer | None = None

  # Кеш данных для detail-панелей
  _agents_data: list[Agent] = []
  _tasks_data: list[Task] = []
  _agents_map: dict[int, Agent] = {}

  def compose(self) -> ComposeResult:
    yield Header(show_clock=True)
    yield StatsBar()

    with TabbedContent(initial="tab-overview", id="tabs"):
      # Вкладка 1: Обзор (сетка 2x2)
      with TabPane("📊 Обзор", id="tab-overview"), Vertical(classes="full-tab-content"):
        with Horizontal(id="overview-top"):
          yield OverviewAgentsPanel()
          yield OverviewTasksPanel()
        with Horizontal(id="overview-bottom"):
          yield OverviewLocksPanel()
          yield OverviewActivityPanel()

      # Вкладка 2: Агенты
      with TabPane("🤖 Агенты", id="tab-agents"), Vertical(classes="full-tab-content"):
        yield DataTable(id="agents-table", cursor_type="row")
        yield Static(
          "[dim]Выберите агента для просмотра деталей[/dim]",
          id="agent-detail",
          classes="detail-panel",
        )

      # Вкладка 3: Задачи (активные, фильтр по f)
      with TabPane("📋 Задачи", id="tab-tasks"), Vertical(classes="full-tab-content"):
        yield DataTable(id="tasks-table", cursor_type="row")
        yield Static(
          "[dim]Выберите задачу для просмотра деталей[/dim]",
          id="task-detail",
          classes="detail-panel",
        )

      # Вкладка 4: Все задачи (полная история)
      with TabPane("📑 Все задачи", id="tab-all-tasks"), Vertical(classes="full-tab-content"):
        yield DataTable(id="all-tasks-table", cursor_type="row")
        yield Static(
          "[dim]Выберите задачу для просмотра деталей[/dim]",
          id="all-task-detail",
          classes="detail-panel",
        )

      # Вкладка 5: Блокировки
      with TabPane("🔒 Блокировки", id="tab-locks"), Vertical(classes="full-tab-content"):
        yield DataTable(id="locks-table", cursor_type="row")

      # Вкладка 6: Активность (последние 100 записей из БД)
      with TabPane("📜 Активность", id="tab-activity"), VerticalScroll(id="activity-scroll"):
        yield Static("", id="activity-log")

    yield Footer()

  def on_mount(self) -> None:
    self.title = "SWARM Monitor"
    self.sub_title = "q: выход | r: обновить | d: тема | 1-6: вкладки"

    # Колонки полноэкранных таблиц
    agents_dt = self.query_one("#agents-table", DataTable)
    agents_dt.add_columns("", "ID", "Имя", "CLI", "Роль", "Статус", "Задача", "PID", "HB", "Регистрация")

    tasks_dt = self.query_one("#tasks-table", DataTable)
    tasks_dt.add_columns("", "ID", "P", "Статус", "Роль", "Назначен", "Работает", "Зависит", "Описание")

    all_tasks_dt = self.query_one("#all-tasks-table", DataTable)
    all_tasks_dt.add_columns("", "ID", "P", "Статус", "Роль", "Назначен", "Работает", "Зависит", "Создана", "Описание")

    locks_dt = self.query_one("#locks-table", DataTable)
    locks_dt.add_columns("", "ID", "Файл", "Агент", "Задача", "Время блокировки", "Длительность")

    # Первичная загрузка + таймер
    self._refresh_all()
    self.refresh_timer = self.set_interval(2.0, self._refresh_all)

  # ── Обновление данных ────────────────────────────────────────

  def _refresh_all(self) -> None:
    """Загружает данные из БД один раз и обновляет все виджеты."""
    agents = get_all_agents()
    tasks = get_all_tasks()
    locks = get_all_locks()
    events = get_recent_events(limit=100)
    agents_map = {a.agent_id: a for a in agents}

    # Кешируем для detail-панелей
    self._agents_data = agents
    self._tasks_data = tasks
    self._agents_map = agents_map

    # StatsBar
    self.query_one(StatsBar).refresh_data(agents, tasks, locks)

    # Панели обзора
    self.query_one(OverviewAgentsPanel).refresh_data(agents)
    self.query_one(OverviewTasksPanel).refresh_data(tasks)
    self.query_one(OverviewLocksPanel).refresh_data(locks, agents_map)
    self.query_one(OverviewActivityPanel).refresh_data(events, agents_map)

    # Полноэкранные таблицы
    self._refresh_agents_table(agents)
    self._refresh_tasks_table(tasks, agents_map)
    self._refresh_all_tasks_table(tasks, agents_map)
    self._refresh_locks_table(locks, agents_map)
    self._refresh_activity_log(events, agents_map)

  def _refresh_agents_table(self, agents: list[Agent]) -> None:
    """Обновляет полную таблицу агентов."""
    table = self.query_one("#agents-table", DataTable)
    cursor_row = table.cursor_row if table.row_count > 0 else 0
    table.clear()
    now = datetime.now(UTC).replace(tzinfo=None)

    for a in agents:
      icon, color = AGENT_STATUS_ICONS.get(a.status, ("?", "white"))
      task = f"#{a.current_task_id}" if a.current_task_id else "—"
      pid = str(a.pid) if a.pid else "—"
      hb = _fmt_heartbeat(a, now)
      reg = _fmt_dt(a.registered_at)

      table.add_row(
        f"[{color}]{icon}[/{color}]",
        f"[bold]#{a.agent_id}[/bold]",
        f"[bold]{a.name}[/bold]",
        a.cli_type,
        a.role or "—",
        f"[{color}]{a.status.value}[/{color}]",
        task,
        pid,
        hb,
        f"[dim]{reg}[/dim]",
        key=str(a.agent_id),
      )

    if cursor_row < table.row_count:
      table.move_cursor(row=cursor_row)

  def _refresh_tasks_table(
    self,
    tasks: list[Task],
    agents_map: dict[int, Agent],
  ) -> None:
    """Обновляет таблицу активных задач (фильтр done по клавише f)."""
    table = self.query_one("#tasks-table", DataTable)
    cursor_row = table.cursor_row if table.row_count > 0 else 0
    table.clear()

    filtered = tasks if self.show_done else [t for t in tasks if t.status != TaskStatus.DONE]

    for t in filtered:
      icon, color = TASK_STATUS_ICONS.get(t.status, ("?", "white"))
      role = t.target_role or "—"
      assigned = t.target_name or "—"
      depends = f"#{t.depends_on}" if t.depends_on else "—"

      if t.assigned_to:
        agent = agents_map.get(t.assigned_to)
        working = agent.name if agent else f"#{t.assigned_to}"
      else:
        working = "—"

      table.add_row(
        f"[{color}]{icon}[/{color}]",
        f"[bold cyan]#{t.task_id}[/bold cyan]",
        str(t.priority),
        f"[{color}]{t.status.value}[/{color}]",
        role,
        f"[cyan]{assigned}[/cyan]",
        f"[green]{working}[/green]",
        depends,
        _esc(t.description),
        key=str(t.task_id),
      )

    if cursor_row < table.row_count:
      table.move_cursor(row=cursor_row)

  def _refresh_all_tasks_table(
    self,
    tasks: list[Task],
    agents_map: dict[int, Agent],
  ) -> None:
    """Обновляет таблицу ВСЕХ задач (включая done/failed)."""
    table = self.query_one("#all-tasks-table", DataTable)
    cursor_row = table.cursor_row if table.row_count > 0 else 0
    table.clear()

    for t in tasks:
      icon, color = TASK_STATUS_ICONS.get(t.status, ("?", "white"))
      role = t.target_role or "—"
      assigned = t.target_name or "—"
      depends = f"#{t.depends_on}" if t.depends_on else "—"
      created = _fmt_dt(t.created_at)

      if t.assigned_to:
        agent = agents_map.get(t.assigned_to)
        working = agent.name if agent else f"#{t.assigned_to}"
      else:
        working = "—"

      table.add_row(
        f"[{color}]{icon}[/{color}]",
        f"[bold cyan]#{t.task_id}[/bold cyan]",
        str(t.priority),
        f"[{color}]{t.status.value}[/{color}]",
        role,
        f"[cyan]{assigned}[/cyan]",
        f"[green]{working}[/green]",
        depends,
        f"[dim]{created}[/dim]",
        _esc(t.description),
        key=str(t.task_id),
      )

    if cursor_row < table.row_count:
      table.move_cursor(row=cursor_row)

  def _refresh_locks_table(
    self,
    locks: list[FileLock],
    agents_map: dict[int, Agent],
  ) -> None:
    """Обновляет полную таблицу блокировок."""
    table = self.query_one("#locks-table", DataTable)
    cursor_row = table.cursor_row if table.row_count > 0 else 0
    table.clear()
    now = datetime.now(UTC).replace(tzinfo=None)

    for lock in locks:
      agent = agents_map.get(lock.locked_by)
      name = agent.name if agent else f"#{lock.locked_by}"
      locked_at = _fmt_dt(lock.locked_at)
      mins = int((now - lock.locked_at).total_seconds() / 60) if lock.locked_at else 0
      duration = _fmt_duration_mins(mins)
      if mins > 30:
        duration = f"[red]{duration}[/red]"

      table.add_row(
        "[yellow]●[/yellow]",
        f"#{lock.lock_id}",
        f"[bold]{lock.file_path}[/bold]",
        name,
        f"#{lock.task_id}",
        f"[dim]{locked_at}[/dim]",
        duration,
        key=str(lock.lock_id),
      )

    if cursor_row < table.row_count:
      table.move_cursor(row=cursor_row)

  def _refresh_activity_log(
    self,
    events: list[TaskLogEntry],
    agents_map: dict[int, Agent],
  ) -> None:
    """Обновляет полный лог активности (последние 100 записей из БД)."""
    lines = []
    for e in events:
      time_str = e.timestamp.strftime("%H:%M:%S") if e.timestamp else "--:--:--"
      icon, color = EVENT_ICONS.get(e.event, ("•", "white"))
      agent = agents_map.get(e.agent_id) if e.agent_id else None
      agent_name = agent.name if agent else "—"
      task_str = f"[magenta]#{e.task_id:3}[/magenta]" if e.task_id else "     "
      msg = e.message or e.event.value

      lines.append(
        f"[dim]{time_str}[/dim]  [{color}]{icon}[/{color}]  {task_str}  "
        f"[cyan]{agent_name:10}[/cyan]  {_esc(msg)}"
      )

    log = self.query_one("#activity-log", Static)
    log.update("\n".join(lines) if lines else "[dim]Нет событий[/dim]")

  # ── Detail-панели ────────────────────────────────────────────

  def _format_agent_detail(self, agent: Agent) -> str:
    """Форматирует детальную информацию об агенте."""
    now = datetime.now(UTC).replace(tzinfo=None)
    icon, color = AGENT_STATUS_ICONS.get(agent.status, ("?", "white"))
    hb = _fmt_heartbeat(agent, now)
    task = f"#{agent.current_task_id}" if agent.current_task_id else "нет"
    pid = str(agent.pid) if agent.pid else "—"
    alive = ""
    if agent.pid is not None:
      alive = " [green](жив)[/green]" if is_process_alive(agent.pid) else " [red](мёртв)[/red]"

    return (
      f"[bold]═══ Агент: {agent.name} ({agent.cli_type}/{agent.role}) ═══[/bold]\n"
      f"ID: [cyan]#{agent.agent_id}[/cyan]  │  "
      f"PID: {pid}{alive}  │  "
      f"Статус: [{color}]{icon} {agent.status.value}[/{color}]  │  "
      f"Задача: {task}\n"
      f"Зарегистрирован: [dim]{_fmt_dt(agent.registered_at)}[/dim]  │  "
      f"Heartbeat: {hb}"
    )

  def _format_task_detail(self, task: Task) -> str:
    """Форматирует детальную информацию о задаче."""
    icon, color = TASK_STATUS_ICONS.get(task.status, ("?", "white"))
    agent_name = "—"
    if task.assigned_to and task.assigned_to in self._agents_map:
      agent_name = self._agents_map[task.assigned_to].name

    if task.depends_on:
      dep_task = next((t for t in self._tasks_data if t.task_id == task.depends_on), None)
      dep_status = f" ({dep_task.status.value})" if dep_task else ""
      depends = f"#{task.depends_on}{dep_status}"
    else:
      depends = "—"

    summary = task.summary or "—"

    return (
      f"[bold]═══ Задача #{task.task_id} ═══[/bold]\n"
      f"[bold]Описание:[/bold] {_esc(task.description)}\n"
      f"P{task.priority} [{color}]{icon} {task.status.value}[/{color}]  │  "
      f"Роль: {task.target_role or '—'}  │  "
      f"Назначен: [cyan]{task.target_name or '—'}[/cyan]  │  "
      f"Работает: [green]{agent_name}[/green]  │  "
      f"Зависит: {depends}\n"
      f"Создана: [dim]{_fmt_dt(task.created_at)}[/dim]  │  "
      f"Начата: [dim]{_fmt_dt(task.started_at)}[/dim]  │  "
      f"Завершена: [dim]{_fmt_dt(task.completed_at)}[/dim]\n"
      f"[bold]Summary:[/bold] {_esc(summary)}"
    )

  # ── Обработчики событий ──────────────────────────────────────

  def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
    """Показывает детали при навигации по таблице."""
    if event.row_key is None or event.row_key.value is None:
      return
    table_id = event.data_table.id
    key = event.row_key.value

    if table_id == "agents-table":
      agent = next((a for a in self._agents_data if str(a.agent_id) == key), None)
      if agent:
        detail = self.query_one("#agent-detail", Static)
        detail.update(self._format_agent_detail(agent))

    elif table_id in ("tasks-table", "all-tasks-table"):
      task = next((t for t in self._tasks_data if str(t.task_id) == key), None)
      if task:
        # Определяем нужную detail-панель
        detail_id = "#all-task-detail" if table_id == "all-tasks-table" else "#task-detail"
        detail = self.query_one(detail_id, Static)
        detail.update(self._format_task_detail(task))

  # ── Действия ─────────────────────────────────────────────────

  def action_refresh(self) -> None:
    self._refresh_all()
    self.notify("Данные обновлены", title="Обновление", severity="information")

  def action_toggle_done(self) -> None:
    self.show_done = not self.show_done
    self.notify(f"Показ done: {'вкл' if self.show_done else 'выкл'}")
    self._refresh_all()

  def action_tab_1(self) -> None:
    self.query_one(TabbedContent).active = "tab-overview"

  def action_tab_2(self) -> None:
    self.query_one(TabbedContent).active = "tab-agents"

  def action_tab_3(self) -> None:
    self.query_one(TabbedContent).active = "tab-tasks"

  def action_tab_4(self) -> None:
    self.query_one(TabbedContent).active = "tab-all-tasks"

  def action_tab_5(self) -> None:
    self.query_one(TabbedContent).active = "tab-locks"

  def action_tab_6(self) -> None:
    self.query_one(TabbedContent).active = "tab-activity"

  def action_quit(self) -> None:
    self.exit()


def run_tui():
  """Запускает TUI-монитор."""
  if find_db_path() is None:
    create_console().print("[red]✗ SWARM не инициализирован. Выполните 'swarm init' сначала.[/red]")
    return

  app = SwarmTUI()
  app.run()

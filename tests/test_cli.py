"""
Интеграционные тесты CLI.
"""

import json
import os

from typer.testing import CliRunner

from swarm.cli import app
from swarm.db import DB_FILENAME, get_launch_sessions

runner = CliRunner()


class TestInitCommand:
    """Тесты команды init."""

    def test_init_creates_database(self, tmp_path, monkeypatch):
        """Проверяет создание БД."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (tmp_path / DB_FILENAME).exists()
        assert "инициализирован" in result.stdout

    def test_init_creates_skills(self, tmp_path, monkeypatch):
        """Проверяет создание скиллов для агентов и оркестратора."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        # Скиллы агентов
        assert (tmp_path / ".claude" / "skills" / "swarm-agent" / "SKILL.md").exists()
        assert (tmp_path / ".codex" / "skills" / "swarm-agent" / "SKILL.md").exists()
        # Скилл оркестратора
        assert (tmp_path / ".claude" / "skills" / "swarm-orchestrator" / "SKILL.md").exists()

        skill_text = (tmp_path / ".codex" / "skills" / "swarm-agent" / "SKILL.md").read_text(encoding="utf-8")
        assert "одна активная блокировка на агента" in skill_text
        assert "swarm heartbeat --agent" in skill_text
        assert "Не используй `swarm --help`" in skill_text


class TestHelpSuppression:
    """Тесты отключения встроенной справки."""

    def test_root_help_is_disabled(self):
        """Корневой --help не должен раскрывать список команд."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code != 0
        assert "No such option: --help" in result.stderr
        assert "Commands" not in result.stderr
        assert "init" not in result.stderr

    def test_subcommand_help_is_disabled(self):
        """Подкоманды не должны поддерживать --help."""
        result = runner.invoke(app, ["task", "add", "--help"])

        assert result.exit_code != 0
        assert "No such option: --help" in result.stderr
        assert "Описание задачи" not in result.stderr

    def test_no_args_do_not_show_command_catalog(self):
        """Запуск без аргументов не должен печатать каталог команд."""
        result = runner.invoke(app, [])

        assert result.exit_code != 0
        assert "Missing command" in result.stderr
        assert "Commands" not in result.stderr
        assert "join" not in result.stderr

    def test_init_refuses_without_force(self, tmp_path, monkeypatch):
        """Проверяет отказ перезаписи без --force."""
        monkeypatch.chdir(tmp_path)

        # Первая инициализация
        runner.invoke(app, ["init"])

        # Попытка повторной
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "уже существует" in result.stdout

    def test_init_force_recreates(self, tmp_path, monkeypatch):
        """Проверяет пересоздание с --force."""
        monkeypatch.chdir(tmp_path)

        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init", "--force"])

        assert result.exit_code == 0
        assert "инициализирован" in result.stdout


class TestTaskCommands:
    """Тесты команд управления задачами."""

    def test_task_add(self, tmp_path, monkeypatch):
        """Проверяет создание задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(
            app,
            [
                "task",
                "add",
                "--desc",
                "Тестовая задача",
                "--priority",
                "1",
            ],
        )

        assert result.exit_code == 0
        assert "Задача #1 создана" in result.stdout

    def test_task_add_with_filters(self, tmp_path, monkeypatch):
        """Проверяет создание задачи с фильтрами."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(
            app,
            [
                "task",
                "add",
                "--desc",
                "Задача для архитектора",
                "--role",
                "architect",
                "--cli",
                "claude",
            ],
        )

        assert result.exit_code == 0
        assert "role=architect" in result.stdout
        assert "cli=claude" in result.stdout

    def test_task_list_empty(self, tmp_path, monkeypatch):
        """Проверяет пустой список задач."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["task", "list"])

        assert result.exit_code == 0
        assert "Задач не найдено" in result.stdout

    def test_task_list_with_tasks(self, tmp_path, monkeypatch):
        """Проверяет список с задачами."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача 1", "--priority", "1"])
        runner.invoke(app, ["task", "add", "--desc", "Задача 2", "--priority", "2"])

        result = runner.invoke(app, ["task", "list"])

        assert result.exit_code == 0
        assert "Задача 1" in result.stdout
        assert "Задача 2" in result.stdout


class TestAgentCommands:
    """Тесты команд агентов."""

    def test_join_interactive(self, tmp_path, monkeypatch):
        """Проверяет регистрацию агента."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(
            app,
            [
                "join",
                "--cli",
                "claude",
                "--name",
                "test-agent",
                "--role",
                "developer",
            ],
        )

        assert result.exit_code == 0
        assert "Зарегистрирован как агент #1" in result.stdout
        # Файл сессии в .swarm/sessions/
        assert (tmp_path / ".swarm" / "sessions" / ".swarm_session_test-agent").exists()

    def test_agents_empty(self, tmp_path, monkeypatch):
        """Проверяет пустой список агентов."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["agents"])

        assert result.exit_code == 0
        assert "агентов нет" in result.stdout

    def test_agents_with_registered(self, tmp_path, monkeypatch):
        """Проверяет список с агентами."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "alice", "--role", "developer"])

        result = runner.invoke(app, ["agents"])

        assert result.exit_code == 0
        assert "alice" in result.stdout
        assert "claude" in result.stdout

    def test_status_not_registered(self, tmp_path, monkeypatch):
        """Проверяет ошибку статуса без регистрации."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "не зарегистрирован" in result.stdout

    def test_status_registered(self, tmp_path, monkeypatch):
        """Проверяет статус зарегистрированного агента."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "bob", "--role", "tester"])

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "bob" in result.stdout
        assert "tester" in result.stdout

    def test_heartbeat_updates_agent(self, tmp_path, monkeypatch):
        """Проверяет отдельную команду heartbeat."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "bob", "--role", "tester"])

        result = runner.invoke(app, ["heartbeat"])

        assert result.exit_code == 0
        assert "Heartbeat обновлён" in result.stdout


class TestNextAndDone:
    """Тесты получения и завершения задач."""

    def test_next_no_tasks(self, tmp_path, monkeypatch):
        """Проверяет поведение при отсутствии задач."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])

        result = runner.invoke(app, ["next"])

        assert result.exit_code == 0
        assert "Нет подходящих задач" in result.stdout

    def test_next_gets_task(self, tmp_path, monkeypatch):
        """Проверяет получение задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Реализовать функцию", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])

        result = runner.invoke(app, ["next"])

        assert result.exit_code == 0
        assert "Задача #1" in result.stdout
        assert "Реализовать функцию" in result.stdout

    def test_done_completes_task(self, tmp_path, monkeypatch):
        """Проверяет завершение задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])
        runner.invoke(app, ["next"])

        result = runner.invoke(app, ["done", "--summary", "Готово"])

        assert result.exit_code == 0
        assert "Задача #1 завершена" in result.stdout

    def test_done_without_task_fails(self, tmp_path, monkeypatch):
        """Проверяет ошибку завершения без задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])

        result = runner.invoke(app, ["done", "--summary", "Что-то"])

        assert result.exit_code == 1
        assert "нет активной задачи" in result.stdout


class TestPermissions:
    """Тесты ограничений прав для агента."""

    def test_agent_cannot_add_task(self, tmp_path, monkeypatch):
        """Агент не должен менять очередь задач."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])

        result = runner.invoke(app, ["task", "add", "--desc", "Нельзя", "--priority", "1"])

        assert result.exit_code == 1
        assert "не может изменять очередь задач" in result.stdout

    def test_anonymous_cannot_force_unlock(self, tmp_path, monkeypatch):
        """Анонимный процесс без сессии не должен использовать --force."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        # Без регистрации агента — анонимный процесс
        result = runner.invoke(app, ["unlock", "--force", "--file", "file.py"])

        assert result.exit_code == 1
        assert "требуется активная сессия" in result.stdout

    def test_agent_can_force_unlock_own_file(self, tmp_path, monkeypatch):
        """Зарегистрированный агент может использовать --force для разблокировки."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])
        runner.invoke(app, ["next"])
        runner.invoke(app, ["lock", "file.py"])

        result = runner.invoke(app, ["unlock", "--force", "--file", "file.py"])

        assert result.exit_code == 0
        assert "разблокирован" in result.stdout.lower()


class TestStartCommand:
    """Тесты команды start."""

    def test_start_no_agents(self, tmp_path, monkeypatch):
        """Проверяет start без агентов."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["start", "--all"])

        assert result.exit_code == 0
        assert "Нет зарегистрированных агентов" in result.stdout

    def test_start_all(self, tmp_path, monkeypatch):
        """Проверяет start --all."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent1", "--role", "developer"])

        # Очищаем переменные окружения для регистрации второго агента
        # (теперь у каждого агента свой файл .swarm_session_<имя>)
        if "SWARM_SESSION" in os.environ:
            del os.environ["SWARM_SESSION"]
        if "SWARM_AGENT" in os.environ:
            del os.environ["SWARM_AGENT"]
        runner.invoke(app, ["join", "--cli", "codex", "--name", "agent2", "--role", "tester"])

        result = runner.invoke(app, ["start", "--all"])

        assert result.exit_code == 0
        assert "2 агентов" in result.stdout


class TestTaskCloseCommand:
    """Тесты команды task close."""

    def test_close_task(self, tmp_path, monkeypatch):
        """Принудительное закрытие задачи через CLI."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Для закрытия", "--priority", "1"])

        result = runner.invoke(app, ["task", "close", "1", "--reason", "Тестовое закрытие"])

        assert result.exit_code == 0
        assert "принудительно закрыта" in result.stdout

    def test_close_nonexistent_task(self, tmp_path, monkeypatch):
        """Закрытие несуществующей задачи даёт ошибку."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["task", "close", "999"])

        assert result.exit_code == 1
        assert "не найдена" in result.stdout

    def test_agent_cannot_close_task(self, tmp_path, monkeypatch):
        """Агент не может закрывать задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])

        result = runner.invoke(app, ["task", "close", "1"])

        assert result.exit_code == 1
        assert "не может изменять очередь задач" in result.stdout


class TestTaskAssignCommand:
    """Тесты команды task assign."""

    def test_assign_task(self, tmp_path, monkeypatch):
        """Назначение задачи через CLI."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Для назначения", "--priority", "1"])

        result = runner.invoke(app, ["task", "assign", "1", "--agent", "worker-1"])

        assert result.exit_code == 0
        assert "назначена" in result.stdout

    def test_assign_nonexistent_task(self, tmp_path, monkeypatch):
        """Назначение несуществующей задачи даёт ошибку."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["task", "assign", "999", "--agent", "x"])

        assert result.exit_code == 1
        assert "не найдена" in result.stdout


class TestTaskResetCommand:
    """Тесты команды task reset."""

    def test_reset_task(self, tmp_path, monkeypatch):
        """Сброс задачи через CLI."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Для сброса", "--priority", "1"])
        # Имитируем in_progress: join + next
        runner.invoke(app, ["join", "--cli", "claude", "--name", "worker", "--role", "developer"])
        runner.invoke(app, ["next"])
        # Убираем сессию агента чтобы стать Лидером
        monkeypatch.delenv("SWARM_AGENT", raising=False)

        result = runner.invoke(app, ["task", "reset", "1"])

        assert result.exit_code == 0
        assert "сброшена в pending" in result.stdout

    def test_reset_nonexistent_task(self, tmp_path, monkeypatch):
        """Сброс несуществующей задачи даёт ошибку."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["task", "reset", "999"])

        assert result.exit_code == 1
        assert "не найдена" in result.stdout

    def test_agent_cannot_reset_task(self, tmp_path, monkeypatch):
        """Агент не может сбрасывать задачи."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])

        result = runner.invoke(app, ["task", "reset", "1"])

        assert result.exit_code == 1
        assert "не может изменять очередь задач" in result.stdout


class TestLockUnlockCommands:
    """Тесты команд lock и unlock."""

    def test_lock_and_unlock(self, tmp_path, monkeypatch):
        """Полный цикл блокировки и разблокировки."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "locker", "--role", "developer"])
        runner.invoke(app, ["next"])

        # Блокируем
        result = runner.invoke(app, ["lock", "test.py"])
        assert result.exit_code == 0
        assert "Заблокирован" in result.stdout

        # Разблокируем
        result = runner.invoke(app, ["unlock", "--file", "test.py"])
        assert result.exit_code == 0
        assert "разблокирован" in result.stdout.lower()

    def test_lock_without_task_fails(self, tmp_path, monkeypatch):
        """Блокировка без активной задачи даёт ошибку."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "idle-agent", "--role", "developer"])

        result = runner.invoke(app, ["lock", "file.py"])

        assert result.exit_code == 1
        assert "нет активной задачи" in result.stdout

    def test_unlock_all_force(self, tmp_path, monkeypatch):
        """unlock --all --force снимает все блокировки."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Задача", "--priority", "1"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "force-agent", "--role", "developer"])
        runner.invoke(app, ["next"])
        runner.invoke(app, ["lock", "a.py"])

        result = runner.invoke(app, ["unlock", "--all", "--force"])

        assert result.exit_code == 0
        assert "Снято блокировок" in result.stdout

    def test_anonymous_cannot_unlock_all_force(self, tmp_path, monkeypatch):
        """Анонимный процесс не может использовать --all --force."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["unlock", "--all", "--force"])

        assert result.exit_code == 1
        assert "требуется активная сессия" in result.stdout


class TestLogsCommand:
    """Тесты команды logs."""

    def test_logs_empty(self, tmp_path, monkeypatch):
        """Проверяет пустой журнал."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["logs"])

        # При init создаётся только БД, событий пока нет
        # Но после join появятся
        assert result.exit_code == 0

    def test_logs_with_events(self, tmp_path, monkeypatch):
        """Проверяет журнал с событиями."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "agent", "--role", "developer"])

        result = runner.invoke(app, ["logs"])

        assert result.exit_code == 0
        # Текст может быть усечён в таблице, ищем часть
        assert "agent_register" in result.stdout or "зарегистрирован" in result.stdout

    def test_logs_with_limit(self, tmp_path, monkeypatch):
        """Проверяет параметр --limit."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "lim-agent", "--role", "developer"])

        result = runner.invoke(app, ["logs", "-n", "5"])

        assert result.exit_code == 0
        assert "лимит: 5" in result.stdout

    def test_logs_with_since(self, tmp_path, monkeypatch):
        """Проверяет параметр --since."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["join", "--cli", "claude", "--name", "since-agent", "--role", "developer"])

        result = runner.invoke(app, ["logs", "--since", "1"])

        assert result.exit_code == 0
        assert "за последние 1.0ч" in result.stdout

    def test_task_add_logs_event(self, tmp_path, monkeypatch):
        """Создание задачи записывает task_created в лог."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "add", "--desc", "Тестовая задача", "--priority", "2"])

        result = runner.invoke(app, ["logs"])

        assert result.exit_code == 0
        assert "task_created" in result.stdout


class TestTerminalCommands:
    """Тесты команды swarm terminal."""

    def test_terminal_launch_dry_run(self, tmp_path, monkeypatch):
        """dry-run создаёт launch session без старта wt."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        from swarm.commands import terminal as terminal_cmd

        monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

        spec = {
            "version": 1,
            "working_directory": str(tmp_path),
            "approval_mode": "safe",
            "layout": {
                "mode": "single",
                "max_panes_per_window": 4,
            },
            "agents": [
                {
                    "cli": "claude",
                    "name": "term-dev-1",
                    "role": "developer",
                    "window": 1,
                    "pane": 1,
                }
            ],
        }
        spec_path = tmp_path / "launch-spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        result = runner.invoke(app, ["terminal", "launch", "--spec", str(spec_path), "--yes", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry-run выполнен" in result.stdout
        assert len(get_launch_sessions()) == 1

    def test_terminal_reconcile_marks_registered(self, tmp_path, monkeypatch):
        """reconcile отображает зарегистрированного агента."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        from swarm.commands import terminal as terminal_cmd

        monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

        spec = {
            "version": 1,
            "working_directory": str(tmp_path),
            "approval_mode": "safe",
            "layout": {
                "mode": "single",
                "max_panes_per_window": 4,
            },
            "agents": [
                {
                    "cli": "claude",
                    "name": "term-reconcile-1",
                    "role": "developer",
                }
            ],
        }
        spec_path = tmp_path / "launch-spec-reconcile.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        launch_result = runner.invoke(app, ["terminal", "launch", "--spec", str(spec_path), "--yes", "--dry-run"])
        assert launch_result.exit_code == 0

        runner.invoke(app, ["join", "--cli", "claude", "--name", "term-reconcile-1", "--role", "developer"])

        session_id = get_launch_sessions()[0].session_id
        reconcile_result = runner.invoke(app, ["terminal", "reconcile", "--session", session_id])

        assert reconcile_result.exit_code == 0
        assert "registered" in reconcile_result.stdout.lower()

    def test_terminal_launch_exclude_cli(self, tmp_path, monkeypatch):
        """--exclude-cli создаёт отдельный spec для исключённых агентов."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        from swarm.commands import terminal as terminal_cmd

        monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

        spec = {
            "version": 1,
            "working_directory": str(tmp_path),
            "approval_mode": "yolo",
            "layout": {
                "mode": "mixed",
                "max_panes_per_window": 4,
            },
            "agents": [
                {"cli": "claude", "name": "arch-1", "role": "architect"},
                {"cli": "codex", "name": "dev-1", "role": "developer"},
                {"cli": "gemini", "name": "front-1", "role": "developer"},
            ],
        }
        spec_path = tmp_path / "launch-spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        result = runner.invoke(
            app,
            ["terminal", "launch", "--spec", str(spec_path), "--exclude-cli", "claude", "--yes", "--dry-run"],
        )

        assert result.exit_code == 0
        # Проверяем, что создан excluded spec
        excluded_path = tmp_path / ".swarm" / "specs" / "launch-spec-excluded.json"
        assert excluded_path.exists()
        excluded_data = json.loads(excluded_path.read_text(encoding="utf-8"))
        assert len(excluded_data["agents"]) == 1
        assert excluded_data["agents"][0]["cli"] == "claude"
        assert excluded_data["agents"][0]["name"] == "arch-1"
        # Проверяем вывод с командой для пользователя
        assert "Ручной запуск" in result.stdout
        assert "swarm terminal launch --spec" in result.stdout

    def test_terminal_stop(self, tmp_path, monkeypatch):
        """stop переводит launch session в stopped."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])

        from swarm.commands import terminal as terminal_cmd

        monkeypatch.setattr(terminal_cmd, "run_preflight", lambda spec, require_wt=True: [])

        spec = {
            "version": 1,
            "working_directory": str(tmp_path),
            "approval_mode": "safe",
            "layout": {
                "mode": "single",
                "max_panes_per_window": 4,
            },
            "agents": [
                {
                    "cli": "claude",
                    "name": "term-stop-1",
                    "role": "developer",
                }
            ],
        }
        spec_path = tmp_path / "launch-spec-stop.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        launch_result = runner.invoke(app, ["terminal", "launch", "--spec", str(spec_path), "--yes", "--dry-run"])
        assert launch_result.exit_code == 0

        session_id = get_launch_sessions()[0].session_id
        stop_result = runner.invoke(app, ["terminal", "stop", "--session", session_id])

        assert stop_result.exit_code == 0
        assert "остановлена" in stop_result.stdout.lower()

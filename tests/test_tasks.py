"""
Тесты распределения и выполнения задач.
"""


from swarm.db import (
    claim_next_task,
    complete_task,
    create_task,
    get_agent_by_session,
    get_file_lock,
    get_task,
    register_agent,
    reset_task,
    try_lock_file,
)
from swarm.models import AgentStatus, TaskStatus


class TestTaskClaiming:
    """Тесты захвата задач."""
    
    def test_claim_task(self, sample_agent, sample_task):
        """Проверяет базовый захват задачи."""
        task = claim_next_task(sample_agent)
        
        assert task is not None
        assert task.task_id == sample_task.task_id
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assigned_to == sample_agent.agent_id
    
    def test_claim_no_tasks(self, sample_agent):
        """Проверяет поведение при пустой очереди."""
        task = claim_next_task(sample_agent)
        
        assert task is None
    
    def test_claim_respects_priority(self, temp_db):
        """Проверяет приоритет при захвате."""
        agent = register_agent("token", "claude", "agent", "developer")
        
        # Создаём задачи с разными приоритетами
        create_task("Низкий приоритет", priority=5)
        high = create_task("Высокий приоритет", priority=1)
        create_task("Средний приоритет", priority=3)
        
        # Должна вернуться задача с высоким приоритетом
        task = claim_next_task(agent)
        
        assert task.task_id == high.task_id
        assert task.priority == 1
    
    def test_claim_respects_role_filter(self, temp_db):
        """Проверяет фильтрацию по роли."""
        developer = register_agent("dev-token", "claude", "dev", "developer")
        architect = register_agent("arch-token", "claude", "arch", "architect")
        
        # Задача только для архитектора
        task = create_task("Дизайн системы", target_role="architect")
        
        # Developer не должен получить задачу
        dev_task = claim_next_task(developer)
        assert dev_task is None
        
        # Architect должен получить
        arch_task = claim_next_task(architect)
        assert arch_task is not None
        assert arch_task.task_id == task.task_id
    
    def test_claim_respects_name_filter(self, temp_db):
        """Проверяет фильтрацию по имени."""
        alice = register_agent("alice-token", "claude", "alice", "developer")
        bob = register_agent("bob-token", "claude", "bob", "developer")
        
        # Задача только для alice
        task = create_task("Задача для Alice", target_name="alice")
        
        # Bob не должен получить
        bob_task = claim_next_task(bob)
        assert bob_task is None
        
        # Alice должна получить
        alice_task = claim_next_task(alice)
        assert alice_task is not None
        assert alice_task.task_id == task.task_id
    
    def test_claim_respects_cli_filter(self, temp_db):
        """Проверяет фильтрацию по типу CLI."""
        claude_agent = register_agent("claude-token", "claude", "agent1", "developer")
        codex_agent = register_agent("codex-token", "codex", "agent2", "developer")
        
        # Задача только для codex
        create_task("Задача для Codex", target_cli="codex")

        # Claude не должен получить
        claude_task = claim_next_task(claude_agent)
        assert claude_task is None
        
        # Codex должен получить
        codex_task = claim_next_task(codex_agent)
        assert codex_task is not None
    
    def test_claim_respects_dependency(self, temp_db):
        """Проверяет зависимости задач."""
        agent = register_agent("token", "claude", "agent", "developer")
        
        # Первая задача
        task1 = create_task("Первая задача")
        # Вторая зависит от первой
        task2 = create_task("Вторая задача", depends_on=task1.task_id)
        
        # Должна вернуться первая задача
        claimed = claim_next_task(agent)
        assert claimed.task_id == task1.task_id
        
        # Завершаем первую
        agent_updated = get_agent_by_session("token")
        complete_task(agent_updated, "Первая готова")
        
        # Теперь вторая должна быть доступна
        claimed2 = claim_next_task(agent)
        assert claimed2 is not None
        assert claimed2.task_id == task2.task_id


class TestTaskCompletion:
    """Тесты завершения задач."""
    
    def test_complete_task(self, temp_db):
        """Проверяет завершение задачи."""
        agent = register_agent("token", "claude", "agent", "developer")
        create_task("Тестовая задача")
        
        # Захватываем задачу
        claim_next_task(agent)
        
        # Получаем обновлённого агента
        agent = get_agent_by_session("token")
        
        # Завершаем
        result = complete_task(agent, "Задача выполнена успешно")
        
        assert result is True
        
        # Проверяем агента
        agent = get_agent_by_session("token")
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task_id is None
    
    def test_complete_releases_locks(self, temp_db):
        """Проверяет снятие блокировок при завершении."""
        agent = register_agent("token", "claude", "agent", "developer")
        task = create_task("Задача")
        
        # Захватываем задачу
        claim_next_task(agent)
        
        # Блокируем файл
        try_lock_file(agent.agent_id, task.task_id, "file1.py")
        
        assert get_file_lock("file1.py") is not None
        
        # Завершаем задачу
        agent = get_agent_by_session("token")
        complete_task(agent, "Готово")
        
        # Блокировки должны быть сняты
        assert get_file_lock("file1.py") is None
    
    def test_complete_without_task_fails(self, sample_agent):
        """Проверяет ошибку при завершении без задачи."""
        result = complete_task(sample_agent, "Резюме")

        assert result is False


class TestTaskReset:
    """Тесты сброса задач."""

    def test_reset_in_progress_task(self, temp_db):
        """Проверяет сброс задачи из in_progress в pending."""
        agent = register_agent("token", "claude", "agent", "developer")
        create_task("Тестовая задача")

        # Захватываем задачу
        task = claim_next_task(agent)
        assert task.status == TaskStatus.IN_PROGRESS

        # Сбрасываем
        result = reset_task(task.task_id)
        assert result is True

        # Проверяем задачу
        updated = get_task(task.task_id)
        assert updated.status == TaskStatus.PENDING
        assert updated.assigned_to is None
        assert updated.target_name is None
        assert updated.started_at is None
        assert updated.summary is None

        # Проверяем агента — должен быть idle
        agent = get_agent_by_session("token")
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task_id is None

    def test_reset_done_task(self, temp_db):
        """Проверяет сброс завершённой задачи."""
        agent = register_agent("token", "claude", "agent", "developer")
        create_task("Задача")

        claim_next_task(agent)
        agent = get_agent_by_session("token")
        complete_task(agent, "Готово")

        task = get_task(1)
        assert task.status == TaskStatus.DONE

        result = reset_task(task.task_id)
        assert result is True

        updated = get_task(task.task_id)
        assert updated.status == TaskStatus.PENDING
        assert updated.summary is None

    def test_reset_releases_locks(self, temp_db):
        """Проверяет снятие блокировок при сбросе."""
        agent = register_agent("token", "claude", "agent", "developer")
        task = create_task("Задача")

        claim_next_task(agent)
        try_lock_file(agent.agent_id, task.task_id, "file1.py")
        assert get_file_lock("file1.py") is not None

        reset_task(task.task_id)
        assert get_file_lock("file1.py") is None

    def test_reset_pending_is_noop(self, temp_db):
        """Проверяет что сброс pending задачи — noop."""
        create_task("Задача")
        result = reset_task(1)
        assert result is True

    def test_reset_nonexistent_task(self, temp_db):
        """Проверяет сброс несуществующей задачи."""
        result = reset_task(999)
        assert result is False

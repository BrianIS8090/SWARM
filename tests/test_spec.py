"""
Тесты модуля валидации и загрузки launch spec (terminal/spec.py).
"""

import json

import pytest

from swarm.terminal.spec import (
  ALLOWED_ROLES,
  LaunchAgentSpec,
  LaunchSpec,
  LayoutSpec,
  _validate_spec,
  load_launch_spec,
  save_launch_spec,
)


def _make_valid_spec(**overrides) -> dict:
  """Создаёт валидный spec-словарь с возможностью переопределения полей."""
  spec = {
    "version": 1,
    "working_directory": "/tmp/project",
    "approval_mode": "safe",
    "layout": {
      "mode": "mixed",
      "max_panes_per_window": 4,
    },
    "agents": [
      {
        "cli": "claude",
        "name": "dev-1",
        "role": "developer",
      },
      {
        "cli": "codex",
        "name": "test-1",
        "role": "tester",
      },
    ],
  }
  spec.update(overrides)
  return spec


class TestValidateSpecPositive:
  """Позитивные тесты валидации spec."""

  def test_valid_spec_passes(self):
    """Корректный spec проходит валидацию без ошибок."""
    data = _make_valid_spec()
    # Не должно бросить исключение
    _validate_spec(data)

  def test_valid_single_layout(self):
    """layout=single с одним агентом проходит валидацию."""
    data = _make_valid_spec(
      layout={"mode": "single", "max_panes_per_window": 1},
      agents=[{"cli": "claude", "name": "solo", "role": "developer"}],
    )
    _validate_spec(data)

  def test_valid_multi_window_layout(self):
    """layout=multi-window проходит валидацию."""
    data = _make_valid_spec(
      layout={"mode": "multi-window", "max_panes_per_window": 2},
    )
    _validate_spec(data)

  def test_all_cli_types(self):
    """Все допустимые CLI-типы проходят валидацию."""
    from swarm.utils import CLI_TYPES

    agents = [
      {"cli": cli, "name": f"agent-{i}", "role": "developer"}
      for i, cli in enumerate(CLI_TYPES)
    ]
    data = _make_valid_spec(agents=agents)
    _validate_spec(data)

  def test_all_roles(self):
    """Все допустимые роли проходят валидацию."""
    agents = [
      {"cli": "claude", "name": f"agent-{i}", "role": role}
      for i, role in enumerate(ALLOWED_ROLES)
    ]
    data = _make_valid_spec(agents=agents)
    _validate_spec(data)

  def test_max_eight_agents(self):
    """Ровно 8 агентов проходят валидацию (максимум)."""
    agents = [
      {"cli": "claude", "name": f"agent-{i}", "role": "developer"}
      for i in range(8)
    ]
    data = _make_valid_spec(agents=agents)
    _validate_spec(data)


class TestValidateSpecNegative:
  """Негативные тесты валидации spec — все ветви ошибок."""

  def test_invalid_version(self):
    """Неверная версия spec вызывает ValueError."""
    data = _make_valid_spec(version=2)
    with pytest.raises(ValueError, match="version=1"):
      _validate_spec(data)

  def test_missing_version(self):
    """Отсутствующая версия вызывает ValueError."""
    data = _make_valid_spec()
    del data["version"]
    with pytest.raises(ValueError, match="version=1"):
      _validate_spec(data)

  def test_empty_working_directory(self):
    """Пустой working_directory вызывает ValueError."""
    data = _make_valid_spec(working_directory="   ")
    with pytest.raises(ValueError, match="working_directory"):
      _validate_spec(data)

  def test_missing_working_directory(self):
    """Отсутствующий working_directory вызывает ValueError."""
    data = _make_valid_spec()
    del data["working_directory"]
    with pytest.raises(ValueError, match="working_directory"):
      _validate_spec(data)

  def test_non_string_working_directory(self):
    """Нестроковый working_directory вызывает ValueError."""
    data = _make_valid_spec(working_directory=123)
    with pytest.raises(ValueError, match="working_directory"):
      _validate_spec(data)

  def test_invalid_approval_mode(self):
    """Невалидный approval_mode вызывает ValueError."""
    data = _make_valid_spec(approval_mode="auto")
    with pytest.raises(ValueError, match="approval_mode"):
      _validate_spec(data)

  def test_missing_layout(self):
    """Отсутствующий layout вызывает ValueError."""
    data = _make_valid_spec()
    del data["layout"]
    with pytest.raises(ValueError, match="layout"):
      _validate_spec(data)

  def test_layout_not_dict(self):
    """layout не словарь вызывает ValueError."""
    data = _make_valid_spec(layout="single")
    with pytest.raises(ValueError, match="layout"):
      _validate_spec(data)

  def test_invalid_layout_mode(self):
    """Невалидный layout.mode вызывает ValueError."""
    data = _make_valid_spec(layout={"mode": "triple", "max_panes_per_window": 4})
    with pytest.raises(ValueError, match="layout.mode"):
      _validate_spec(data)

  def test_invalid_max_panes_zero(self):
    """max_panes_per_window=0 вызывает ValueError."""
    data = _make_valid_spec(layout={"mode": "mixed", "max_panes_per_window": 0})
    with pytest.raises(ValueError, match="max_panes_per_window"):
      _validate_spec(data)

  def test_invalid_max_panes_negative(self):
    """max_panes_per_window отрицательный вызывает ValueError."""
    data = _make_valid_spec(layout={"mode": "mixed", "max_panes_per_window": -1})
    with pytest.raises(ValueError, match="max_panes_per_window"):
      _validate_spec(data)

  def test_invalid_max_panes_not_int(self):
    """max_panes_per_window не целое число вызывает ValueError."""
    data = _make_valid_spec(layout={"mode": "mixed", "max_panes_per_window": "four"})
    with pytest.raises(ValueError, match="max_panes_per_window"):
      _validate_spec(data)

  def test_empty_agents_list(self):
    """Пустой список агентов вызывает ValueError."""
    data = _make_valid_spec(agents=[])
    with pytest.raises(ValueError, match="agents"):
      _validate_spec(data)

  def test_agents_not_list(self):
    """agents не список вызывает ValueError."""
    data = _make_valid_spec(agents="one agent")
    with pytest.raises(ValueError, match="agents"):
      _validate_spec(data)

  def test_too_many_agents(self):
    """Более 8 агентов вызывает ValueError."""
    agents = [
      {"cli": "claude", "name": f"agent-{i}", "role": "developer"}
      for i in range(9)
    ]
    data = _make_valid_spec(agents=agents)
    with pytest.raises(ValueError, match="максимум 8"):
      _validate_spec(data)

  def test_single_layout_requires_one_agent(self):
    """layout=single с несколькими агентами вызывает ValueError."""
    data = _make_valid_spec(
      layout={"mode": "single", "max_panes_per_window": 4},
      agents=[
        {"cli": "claude", "name": "a1", "role": "developer"},
        {"cli": "codex", "name": "a2", "role": "tester"},
      ],
    )
    with pytest.raises(ValueError, match="single"):
      _validate_spec(data)

  def test_agent_not_dict(self):
    """Агент не словарь вызывает ValueError."""
    data = _make_valid_spec(agents=["not-a-dict"])
    with pytest.raises(ValueError, match="должен быть объектом"):
      _validate_spec(data)

  def test_invalid_cli_type(self):
    """Невалидный cli тип агента вызывает ValueError."""
    data = _make_valid_spec(
      agents=[{"cli": "gpt4", "name": "bad-cli", "role": "developer"}],
      layout={"mode": "single", "max_panes_per_window": 4},
    )
    with pytest.raises(ValueError, match="cli"):
      _validate_spec(data)

  def test_missing_agent_name(self):
    """Отсутствующее имя агента вызывает ValueError."""
    data = _make_valid_spec(
      agents=[{"cli": "claude", "role": "developer"}],
      layout={"mode": "single", "max_panes_per_window": 4},
    )
    with pytest.raises(ValueError, match="name"):
      _validate_spec(data)

  def test_agent_name_not_string(self):
    """Нестроковое имя агента вызывает ValueError."""
    data = _make_valid_spec(
      agents=[{"cli": "claude", "name": 123, "role": "developer"}],
      layout={"mode": "single", "max_panes_per_window": 4},
    )
    with pytest.raises(ValueError, match="name"):
      _validate_spec(data)

  def test_invalid_agent_name_format(self):
    """Имя агента с недопустимыми символами вызывает ValueError."""
    data = _make_valid_spec(
      agents=[{"cli": "claude", "name": "bad agent name!", "role": "developer"}],
      layout={"mode": "single", "max_panes_per_window": 4},
    )
    with pytest.raises(ValueError):
      _validate_spec(data)

  def test_duplicate_agent_names(self):
    """Дублирование имён агентов вызывает ValueError."""
    data = _make_valid_spec(
      agents=[
        {"cli": "claude", "name": "same-name", "role": "developer"},
        {"cli": "codex", "name": "same-name", "role": "tester"},
      ],
    )
    with pytest.raises(ValueError, match="дублируется"):
      _validate_spec(data)

  def test_invalid_role(self):
    """Невалидная роль агента вызывает ValueError."""
    data = _make_valid_spec(
      agents=[{"cli": "claude", "name": "agent-1", "role": "manager"}],
      layout={"mode": "single", "max_panes_per_window": 4},
    )
    with pytest.raises(ValueError, match="role"):
      _validate_spec(data)


class TestSaveAndLoadSpec:
  """Тесты round-trip: save_launch_spec -> load_launch_spec."""

  def test_save_and_load_roundtrip(self, tmp_path):
    """Сохранённый spec загружается без потерь."""
    original = LaunchSpec(
      version=1,
      working_directory="/tmp/project",
      approval_mode="yolo",
      layout=LayoutSpec(mode="mixed", max_panes_per_window=3),
      agents=[
        LaunchAgentSpec(cli="claude", name="arch-1", role="architect", window=1, pane=1),
        LaunchAgentSpec(cli="codex", name="dev-1", role="developer"),
      ],
    )

    spec_path = tmp_path / "test-spec.json"
    save_launch_spec(original, spec_path)

    # Проверяем, что файл создан
    assert spec_path.exists()

    # Загружаем обратно
    loaded = load_launch_spec(spec_path)

    assert loaded.version == original.version
    assert loaded.working_directory == original.working_directory
    assert loaded.approval_mode == original.approval_mode
    assert loaded.layout.mode == original.layout.mode
    assert loaded.layout.max_panes_per_window == original.layout.max_panes_per_window
    assert len(loaded.agents) == len(original.agents)

    # Проверяем агентов
    for orig_agent, loaded_agent in zip(original.agents, loaded.agents, strict=True):
      assert loaded_agent.cli == orig_agent.cli
      assert loaded_agent.name == orig_agent.name
      assert loaded_agent.role == orig_agent.role
      assert loaded_agent.window == orig_agent.window
      assert loaded_agent.pane == orig_agent.pane

  def test_load_nonexistent_file(self, tmp_path):
    """Загрузка несуществующего файла вызывает ValueError."""
    path = tmp_path / "nonexistent.json"
    with pytest.raises(ValueError, match="не найден"):
      load_launch_spec(path)

  def test_load_invalid_json(self, tmp_path):
    """Загрузка файла с невалидным JSON вызывает ValueError."""
    path = tmp_path / "bad.json"
    path.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Некорректный JSON"):
      load_launch_spec(path)

  def test_save_creates_utf8_file(self, tmp_path):
    """Сохранённый файл имеет UTF-8 кодировку."""
    spec = LaunchSpec(
      version=1,
      working_directory="/tmp/проект",
      approval_mode="safe",
      layout=LayoutSpec(mode="single"),
      agents=[
        LaunchAgentSpec(cli="claude", name="agent-1", role="developer"),
      ],
    )
    spec_path = tmp_path / "utf8-spec.json"
    save_launch_spec(spec, spec_path)

    raw = spec_path.read_bytes()
    text = raw.decode("utf-8")
    data = json.loads(text)
    assert data["working_directory"] == "/tmp/проект"

  def test_roundtrip_single_layout(self, tmp_path):
    """Round-trip для layout=single."""
    original = LaunchSpec(
      version=1,
      working_directory="/home/user/code",
      approval_mode="safe",
      layout=LayoutSpec(mode="single", max_panes_per_window=1),
      agents=[
        LaunchAgentSpec(cli="gemini", name="solo-1", role="architect"),
      ],
    )
    spec_path = tmp_path / "single-spec.json"
    save_launch_spec(original, spec_path)
    loaded = load_launch_spec(spec_path)

    assert loaded.layout.mode == "single"
    assert len(loaded.agents) == 1
    assert loaded.agents[0].cli == "gemini"

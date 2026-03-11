"""
Тесты утилит SWARM.

Проверяет кеширование и обработку ошибок в get_version().
"""

from unittest.mock import MagicMock, patch

from swarm.utils import get_version


class TestGetVersion:
  """Тесты функции get_version()."""

  def setup_method(self):
    """Сбрасываем кеш lru_cache перед каждым тестом."""
    get_version.cache_clear()

  def test_returns_string(self):
    """get_version() возвращает строку."""
    result = get_version()
    assert isinstance(result, str)
    assert len(result) > 0

  def test_cached_second_call(self):
    """Повторный вызов не читает файл снова (используется кеш)."""
    with patch("swarm.utils.Path") as mock_path_cls:
      # Настраиваем мок для имитации чтения файла
      mock_file = MagicMock()
      mock_file.read_text.return_value = '{"version": "1.0.0"}'
      mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_file)

      # Первый вызов — читает файл
      result1 = get_version()
      # Второй вызов — из кеша
      result2 = get_version()

      assert result1 == result2
      # read_text вызван максимум один раз (кеш работает)
      assert mock_file.read_text.call_count <= 1

  def test_file_not_found_returns_unknown(self):
    """При отсутствии version.json возвращает 'unknown'."""
    get_version.cache_clear()
    with patch("swarm.utils.Path") as mock_path_cls:
      # Имитируем FileNotFoundError при чтении
      mock_file = MagicMock()
      mock_file.read_text.side_effect = FileNotFoundError("Файл не найден")
      mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_file)

      result = get_version()
      assert result == "unknown"

  def test_invalid_json_returns_unknown(self):
    """При невалидном JSON возвращает 'unknown'."""
    get_version.cache_clear()
    with patch("swarm.utils.Path") as mock_path_cls:
      # Имитируем битый JSON
      mock_file = MagicMock()
      mock_file.read_text.return_value = "not a json"
      mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_file)

      result = get_version()
      assert result == "unknown"

  def test_missing_version_key_returns_unknown(self):
    """При отсутствии ключа 'version' в JSON возвращает 'unknown'."""
    get_version.cache_clear()
    with patch("swarm.utils.Path") as mock_path_cls:
      # JSON без ключа version
      mock_file = MagicMock()
      mock_file.read_text.return_value = '{"name": "swarm"}'
      mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_file)

      result = get_version()
      assert result == "unknown"

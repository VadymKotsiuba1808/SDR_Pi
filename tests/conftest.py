"""
Глобальні фікстури та налаштування для всіх тестів.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_system_modules():
    """
    Глобально підміняє системно-залежні модулі, щоб уникнути зависань
    та побічних ефектів під час ініціалізації сервісів (наприклад, KeyboardService).
    """
    with patch.dict(
        "sys.modules",
        {
            "keyboard": MagicMock(),
            "win32api": MagicMock(),
            "win32gui": MagicMock(),
            "win32con": MagicMock(),
            "pynput": MagicMock(),
            "pynput.keyboard": MagicMock(),
        },
    ):
        yield

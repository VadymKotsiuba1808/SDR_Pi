"""Конфігурація pytest та глобальні фікстури для ізоляції тестів."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_system_modules() -> Generator[None, None, None]:
    """Підміна системних модулів (keyboard, win32api) для ізоляції тестів."""
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

"""
Конфігураційний модуль для pytest.

Цей модуль містить глобальні фікстури, налаштування та хуки, які автоматично
застосовуються до всіх тестів у проекті. Він забезпечує ізоляцію тестів від
системно-залежних бібліотек та зовнішнього середовища.
"""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_system_modules() -> Generator[None, None, None]:
    """
    Глобально підміняє системно-залежні модулі.

    Ця фікстура запобігає спробам ініціалізації низькорівневих бібліотек для
    взаємодії з клавіатурою та вікнами (keyboard, win32api тощо) під час тестів.
    Це критично для роботи в середовищах CI та запобігання побічним ефектам
    на робочому столі розробника.

    Yields:
        None: Фікстура працює як контекстний менеджер для патчингу `sys.modules`.
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

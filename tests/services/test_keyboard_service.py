"""
Модуль містить юніт-тести для KeyboardService.

Ці тести перевіряють логіку керування розкладкою клавіатури, враховуючи
платформозалежність (Windows/Linux) та коректність виклику системних API.
"""

from typing import Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

from app.services.keyboard_service import KeyboardService


@pytest.fixture
def mock_system_win() -> MagicMock:
    """Створює мок-об'єкт системної інформації для Windows."""
    system = MagicMock()
    system.is_windows = True
    system.is_linux = False
    return system


@pytest.fixture
def mock_system_linux() -> MagicMock:
    """Створює мок-об'єкт системної інформації для Linux."""
    system = MagicMock()
    system.is_windows = False
    system.is_linux = True
    return system


@pytest.fixture
def mock_modules() -> Generator[Dict[str, MagicMock], None, None]:
    """Фікстура для підміни системних модулів."""
    mock_keyboard = MagicMock()
    mock_win32api = MagicMock()
    mock_win32gui = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "keyboard": mock_keyboard,
            "win32api": mock_win32api,
            "win32gui": mock_win32gui,
            "pynput": MagicMock(),
            "pynput.keyboard": MagicMock(),
        },
    ):
        yield {
            "keyboard": mock_keyboard,
            "win32api": mock_win32api,
            "win32gui": mock_win32gui,
        }


def test_keyboard_initialization_win(
    mock_system_win: MagicMock, mock_modules: Dict[str, MagicMock]
) -> None:
    """Перевіряє ініціалізацію KeyboardService на Windows."""
    service = KeyboardService(mock_system_win)
    assert service.current_layout == "EN", "Initial layout should be EN by default"
    assert mock_modules["keyboard"].add_hotkey.called, (
        "Hot key for switching should be registered"
    )


def test_keyboard_toggle_layout(
    mock_system_win: MagicMock, mock_modules: Dict[str, MagicMock]
) -> None:
    """Перевіряє циклічне перемикання розкладки."""
    service = KeyboardService(mock_system_win)
    # Скидаємо виклик з ініціалізації, щоб перевірити саме наступний виклик toggle
    mock_modules["win32api"].LoadKeyboardLayout.reset_mock()

    service.toggle_layout()
    assert service.current_layout == "UA", "Layout should change to UA after switching"
    assert mock_modules["win32api"].LoadKeyboardLayout.called, (
        "Windows API should be called for UA"
    )

    service.toggle_layout()
    assert service.current_layout == "EN", (
        "Layout should return to EN after second switch"
    )


def test_keyboard_callback(
    mock_system_win: MagicMock, mock_modules: Dict[str, MagicMock]
) -> None:
    """Перевіряє виклик callback-функції при зміні розкладки."""
    callback = MagicMock()
    service = KeyboardService(mock_system_win, callback=callback)
    service.toggle_layout()
    callback.assert_called_once_with("UA")


@pytest.mark.skipif(reason="Залежить від наявності бібліотек win32 на системі")
def test_windows_layout_apply(mock_system_win: MagicMock) -> None:
    """Перевіряє виклик специфічних API Windows для застосування розкладки."""
    service = KeyboardService(mock_system_win)

    # Використовуємо setattr, щоб підмінити динамічно імпортовані модулі моками
    mock_win32api = MagicMock()
    mock_win32gui = MagicMock()

    setattr(service, "win32api", mock_win32api)
    setattr(service, "win32gui", mock_win32gui)

    service.current_layout = "UA"
    service._set_windows_layout()

    # Перевіряємо виклик з ідентифікатором української розкладки (0x0422)
    # та прапором KLF_ACTIVATE (1)
    mock_win32api.LoadKeyboardLayout.assert_called_with("00000422", 1)

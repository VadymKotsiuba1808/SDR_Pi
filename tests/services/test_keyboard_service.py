"""
Тести для сервісу розкладки клавіатури (KeyboardService).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.keyboard_service import KeyboardService


@pytest.fixture
def mock_system_win():
    system = MagicMock()
    system.is_windows = True
    system.is_linux = False
    return system


@pytest.fixture
def mock_system_linux():
    system = MagicMock()
    system.is_windows = False
    system.is_linux = True
    return system


def test_keyboard_initialization_win(mock_system_win):
    """Тест ініціалізації на Windows."""
    with patch("keyboard.add_hotkey") as mock_hotkey:
        service = KeyboardService(mock_system_win)
        assert service.current_layout == "EN"
        assert mock_hotkey.called


def test_keyboard_toggle_layout(mock_system_win):
    """Тест перемикання розкладки."""
    # Відключаємо реальні виклики API
    with patch.object(KeyboardService, "_apply_layout"):
        service = KeyboardService(mock_system_win)

        service.toggle_layout()
        assert service.current_layout == "UA"

        service.toggle_layout()
        assert service.current_layout == "EN"


def test_keyboard_callback(mock_system_win):
    """Тест виклику callback при зміні розкладки."""
    callback = MagicMock()
    with patch.object(KeyboardService, "_apply_layout"):
        service = KeyboardService(mock_system_win, callback=callback)
        service.toggle_layout()
        callback.assert_called_once_with("UA")


@pytest.mark.skipif(reason="Залежить від наявності бібліотек win32 на системі")
def test_windows_layout_apply(mock_system_win: MagicMock) -> None:
    """Тест виклику специфічних API Windows."""
    service = KeyboardService(mock_system_win)

    # Використовуємо кастування типів до Any, щоб Pylance дозволив підмінити модуль на Mock
    mock_win32api = MagicMock()
    mock_win32gui = MagicMock()

    setattr(service, "win32api", mock_win32api)
    setattr(service, "win32gui", mock_win32gui)

    service.current_layout = "UA"
    service._set_windows_layout()

    # Звертаємося до нашого локального mock_win32api, щоб уникнути помилки "not an attribute of None"
    mock_win32api.LoadKeyboardLayout.assert_called_with("00000422", 1)

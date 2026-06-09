"""
Тести для віджета перемикання розкладки клавіатури (KeyboardWidget).
"""

from unittest.mock import MagicMock

import pytest

from app.widgets.keyboard_widget import KeyboardWidget


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def mock_keyboard_service():
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def keyboard_widget(qtbot, mock_settings, mock_keyboard_service):
    widget = KeyboardWidget(mock_settings, mock_keyboard_service)
    qtbot.addWidget(widget)
    yield widget
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.removeTranslator(widget.translator)


def test_initial_layout_display(keyboard_widget, mock_keyboard_service):
    """Тест початкового відображення розкладки в ComboBox."""
    assert keyboard_widget.ui.langComboBox.currentText() == "EN"


def test_ui_change_triggers_service(keyboard_widget, mock_keyboard_service):
    """Тест зміни розкладки через GUI (ComboBox)."""
    # Змінюємо в UI на UA
    keyboard_widget.ui.langComboBox.setCurrentText("UA")

    # Має викликати перемикання в сервісі
    assert mock_keyboard_service.toggle_layout.called


def test_service_update_updates_ui(keyboard_widget):
    """Тест оновлення UI при зміні стану в сервісі (через callback)."""
    # Імітуємо виклик callback від сервісу
    keyboard_widget.update_ui_silent("UA")
    assert keyboard_widget.ui.langComboBox.currentText() == "UA"

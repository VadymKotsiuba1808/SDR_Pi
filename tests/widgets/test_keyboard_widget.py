"""Тести для віджета перемикання розкладки клавіатури."""

from typing import Generator
from unittest.mock import MagicMock

import pytest

from app.widgets.keyboard_widget import KeyboardWidget


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def mock_keyboard_service() -> MagicMock:
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def keyboard_widget(
    qtbot, mock_settings: MagicMock, mock_keyboard_service: MagicMock
) -> Generator[KeyboardWidget, None, None]:
    widget = KeyboardWidget(mock_settings, mock_keyboard_service)
    qtbot.addWidget(widget)
    yield widget
    from PyQt6.QtCore import QCoreApplication

    # Очищення перекладача
    QCoreApplication.removeTranslator(widget.translator)


def test_initial_layout_display(
    keyboard_widget: KeyboardWidget, mock_keyboard_service: MagicMock
) -> None:
    assert keyboard_widget.ui.langComboBox.currentText() == "EN", (
        "ComboBox should display initial layout from service"
    )


def test_ui_change_triggers_service(
    keyboard_widget: KeyboardWidget, mock_keyboard_service: MagicMock
) -> None:
    keyboard_widget.ui.langComboBox.setCurrentText("UA")
    assert mock_keyboard_service.toggle_layout.called, (
        "toggle_layout should be called when ComboBox text changes"
    )


def test_service_update_updates_ui(keyboard_widget: KeyboardWidget) -> None:
    keyboard_widget.update_ui_silent("UA")
    assert keyboard_widget.ui.langComboBox.currentText() == "UA", (
        "UI should update according to the provided layout code"
    )

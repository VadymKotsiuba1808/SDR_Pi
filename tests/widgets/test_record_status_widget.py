"""Тести для віджета статусу запису."""

import pytest
from pytestqt.qtbot import QtBot

from app.widgets.record_status_widget import RecordingStatusWidget


@pytest.fixture
def status_widget(qtbot: QtBot) -> RecordingStatusWidget:
    """Фікстура для створення та ініціалізації віджета статусу запису."""
    widget = RecordingStatusWidget()
    qtbot.addWidget(widget)
    return widget


def test_initial_visibility(status_widget: RecordingStatusWidget) -> None:
    """Перевірка початкової видимості віджета."""
    assert status_widget.isVisible() is False, "Widget should be hidden initially"


def test_update_duration(status_widget: RecordingStatusWidget) -> None:
    """Перевірка оновлення тексту таймера запису."""
    duration = "01:23:45"
    status_widget.update_duration(duration)
    assert status_widget.ui.duration_label.text() == duration, "Timer text mismatch"


def test_on_pause_toggled(status_widget: RecordingStatusWidget) -> None:
    """Перевірка зміни стану індикатора при перемиканні паузи."""
    # Знімаємо з паузи (активний стан індикатора)
    status_widget.on_pause_toggled(False)
    assert status_widget.ui.rec_label.property("active") is True, (
        "REC indicator should be active"
    )

    # Ставимо на паузу (неактивний стан індикатора)
    status_widget.on_pause_toggled(True)
    assert status_widget.ui.rec_label.property("active") is False, (
        "REC indicator should be inactive"
    )


def test_reset_state(status_widget: RecordingStatusWidget) -> None:
    """Перевірка повного скидання стану віджета."""
    # Встановлюємо довільний стан
    status_widget.setVisible(True)
    status_widget.ui.pause_button.setChecked(True)
    status_widget.update_duration("00:10:00")

    # Скидаємо стан
    status_widget.reset_state()

    # Перевіряємо повернення до значень за замовчуванням
    assert status_widget.isVisible() is False, "Widget should be hidden after reset"
    assert status_widget.ui.pause_button.isChecked() is False, (
        "Pause button should be unchecked"
    )
    assert status_widget.ui.duration_label.text() == "00:00:00", (
        "Timer should be reset to 00:00:00"
    )

"""
Тести для віджета статусу запису (RecordingStatusWidget).
"""

import pytest

from app.widgets.record_status_widget import RecordingStatusWidget


@pytest.fixture
def status_widget(qtbot):
    """Фікстура для ініціалізації RecordingStatusWidget."""
    widget = RecordingStatusWidget()
    qtbot.addWidget(widget)
    return widget


def test_initial_visibility(status_widget):
    """Тест початкового стану (має бути прихований)."""
    assert status_widget.isVisible() is False


def test_update_duration(status_widget):
    """Тест оновлення тексту таймера."""
    status_widget.update_duration("01:23:45")
    assert status_widget.ui.duration_label.text() == "01:23:45"


def test_on_pause_toggled(status_widget):
    """Тест зміни стану індикатора при паузі."""
    # Знімаємо з паузи (активний)
    status_widget.on_pause_toggled(False)
    assert status_widget.ui.rec_label.property("active") is True

    # Ставимо на паузу (неактивний)
    status_widget.on_pause_toggled(True)
    assert status_widget.ui.rec_label.property("active") is False


def test_reset_state(status_widget):
    """Тест скидання стану віджета."""
    status_widget.setVisible(True)
    status_widget.ui.pause_button.setChecked(True)
    status_widget.update_duration("00:10:00")

    status_widget.reset_state()

    assert status_widget.isVisible() is False
    assert status_widget.ui.pause_button.isChecked() is False
    assert status_widget.ui.duration_label.text() == "00:00:00"

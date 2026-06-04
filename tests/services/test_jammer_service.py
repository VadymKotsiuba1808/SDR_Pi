"""Юніт-тести для JammerService."""

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QDateTime

from app.services.jammer_service import JammerService


@pytest.fixture
def mock_pi_network():
    return MagicMock()


@pytest.fixture
def mock_jammer_settings():
    settings = MagicMock()
    settings.main_relays = ["K1", "K2"]
    settings.is_jammer_auto_stop_enabled = False
    settings.jammer_auto_stop_interval_s = 60
    return settings


@pytest.fixture
def jammer_service(mock_pi_network, mock_jammer_settings):
    service = JammerService(mock_pi_network, mock_jammer_settings)
    yield service
    service.stop()


def test_jammer_start(jammer_service, mock_pi_network, mock_jammer_settings):
    jammer_service.start()

    assert jammer_service.is_active is True, "Jammer should be active after start()"
    assert jammer_service.start_time is not None, (
        "Start time should be set after start()"
    )
    mock_pi_network.request_alarm_start.assert_called_once_with(["K1", "K2"])


def test_jammer_stop(jammer_service, mock_pi_network):
    jammer_service.start()
    jammer_service.stop()

    assert jammer_service.is_active is False, "Jammer should not be active after stop()"
    assert jammer_service.start_time is None, (
        "Start time should be cleared after stop()"
    )
    mock_pi_network.request_alarm_stop.assert_called_once()


def test_jammer_auto_stop(jammer_service, mock_jammer_settings, qtbot):
    mock_jammer_settings.is_jammer_auto_stop_enabled = True
    mock_jammer_settings.jammer_auto_stop_interval_s = 60

    jammer_service.start()

    assert jammer_service.auto_stop_timer.isActive(), (
        "Auto-stop timer should be running"
    )
    assert jammer_service.is_active is True, "Jammer should be active"

    # Емулюємо сигнал таймера для перевірки реакції без реального очікування
    jammer_service.auto_stop_timer.timeout.emit()

    assert jammer_service.is_active is False, "Jammer should stop by timer signal"


def test_get_formatted_time(jammer_service):
    assert jammer_service.get_formatted_time() == "00:00:00", (
        "Initial time should be 00:00:00"
    )

    jammer_service.start()
    # Штучно зміщуємо час старту на 01:05:10 назад для перевірки розрахунку
    jammer_service.start_time = QDateTime.currentDateTime().addSecs(-(3600 + 300 + 10))

    assert jammer_service.get_formatted_time() == "01:05:10", (
        "Mismatch of formatted time after start"
    )

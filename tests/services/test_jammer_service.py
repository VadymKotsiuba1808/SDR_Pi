"""
Тести для сервісу глушилки (JammerService).
"""

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
    return JammerService(mock_pi_network, mock_jammer_settings)


def test_jammer_start(jammer_service, mock_pi_network, mock_jammer_settings):
    """Тест запуску глушилки."""
    jammer_service.start()

    assert jammer_service.is_active is True
    assert jammer_service.start_time is not None
    mock_pi_network.request_alarm_start.assert_called_once_with(["K1", "K2"])


def test_jammer_stop(jammer_service, mock_pi_network):
    """Тест зупинки глушилки."""
    jammer_service.start()
    jammer_service.stop()

    assert jammer_service.is_active is False
    assert jammer_service.start_time is None
    mock_pi_network.request_alarm_stop.assert_called_once()


def test_jammer_auto_stop(jammer_service, mock_jammer_settings, qtbot):
    """Тест автоматичної зупинки за таймером."""
    mock_jammer_settings.is_jammer_auto_stop_enabled = True
    mock_jammer_settings.jammer_auto_stop_interval_s = 1  # 1 секунда

    # Використовуємо callback для перевірки конкретного значення сигналу
    def check_signal(val):
        return val is False

    jammer_service.start()

    # Чекаємо сигналу вимкнення (False)
    with qtbot.waitSignal(
        jammer_service.state_changed, timeout=2000, check_params_cb=check_signal
    ):
        pass

    assert jammer_service.is_active is False


def test_get_formatted_time(jammer_service):
    """Тест форматування часу роботи."""
    assert jammer_service.get_formatted_time() == "00:00:00"

    jammer_service.start()
    # Штучно зміщуємо час старту на 1 годину 5 хвилин 10 секунд назад
    jammer_service.start_time = QDateTime.currentDateTime().addSecs(-(3600 + 300 + 10))

    assert jammer_service.get_formatted_time() == "01:05:10"

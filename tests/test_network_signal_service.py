"""
Тести для сервісу мережевого сигналу (NetworkSignalService).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.network_signal_service import NetworkSignalService


@pytest.fixture
def mock_system():
    system = MagicMock()
    system.is_windows = True
    system.is_linux = False
    return system


@pytest.fixture
def signal_service(mock_system):
    return NetworkSignalService(mock_system)


def test_get_windows_wifi_signal_success(signal_service):
    """Тест парсингу netsh на Windows."""
    mock_output = "Interface name : Wi-Fi\nSignal : 85%\n"
    with patch("subprocess.check_output", return_value=mock_output):
        signal = signal_service._get_windows_wifi_signal()
        assert signal == 85


def test_get_linux_wifi_signal_nmcli(signal_service):
    """Тест парсингу nmcli на Linux."""
    signal_service.system_service.is_windows = False
    signal_service.system_service.is_linux = True

    mock_output = "no:SSID1:40\nyes:MyWiFi:92\n"
    with patch("subprocess.check_output", return_value=mock_output):
        signal = signal_service._get_linux_wifi_signal()
        assert signal == 92


def test_connectivity_check(signal_service):
    """Тест перевірки інтернет-з'єднання."""
    with patch("socket.create_connection") as mock_conn:
        # Успішне підключення
        mock_conn.return_value = MagicMock()
        assert signal_service._check_internet_connectivity() is True

        # Помилка підключення
        mock_conn.side_effect = TimeoutError()
        assert signal_service._check_internet_connectivity() is False


def test_get_signal_strength_flow(signal_service):
    """Тест пріоритетів: WiFi -> Wired -> None."""
    # 1. WiFi знайдено
    with patch.object(signal_service, "_get_wifi_signal", return_value=75):
        assert signal_service.get_signal_strength() == 75

    # 2. WiFi немає, але є дріт
    with patch.object(signal_service, "_get_wifi_signal", return_value=None):
        with patch.object(signal_service, "_has_wired_connection", return_value=True):
            assert signal_service.get_signal_strength() == 100

    # 3. Нічого немає
    with patch.object(signal_service, "_get_wifi_signal", return_value=None):
        with patch.object(signal_service, "_has_wired_connection", return_value=False):
            assert signal_service.get_signal_strength() == 0

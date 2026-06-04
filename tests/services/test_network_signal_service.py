"""Тести для сервісу мережевого сигналу (NetworkSignalService)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.services.network_signal_service import NetworkSignalService


@pytest.fixture
def mock_system() -> MagicMock:
    """Створює мок-об'єкт системного сервісу."""
    system = MagicMock()
    # Імітуємо ОС залежно від платформи, на якій запущено тести
    system.is_windows = sys.platform == "win32"
    system.is_linux = sys.platform == "linux"
    return system


@pytest.fixture
def signal_service(mock_system: MagicMock) -> NetworkSignalService:
    """Створює екземпляр NetworkSignalService для тестування."""
    return NetworkSignalService(mock_system)


def test_os_branch_selection_windows(signal_service: NetworkSignalService) -> None:
    """Перевіряє вибір логіки отримання сигналу для Windows."""
    signal_service.system_service.is_windows = True
    signal_service.system_service.is_linux = False

    with patch.object(
        signal_service, "_get_windows_wifi_signal", return_value=85
    ) as mock_win:
        with patch.object(signal_service, "_get_linux_wifi_signal") as mock_lin:
            signal = signal_service._get_wifi_signal()
            assert signal == 85, "Signal level 85 was expected"
            mock_win.assert_called_once()
            mock_lin.assert_not_called()


def test_os_branch_selection_linux(signal_service: NetworkSignalService) -> None:
    """Перевіряє вибір логіки отримання сигналу для Linux."""
    signal_service.system_service.is_windows = False
    signal_service.system_service.is_linux = True

    with patch.object(
        signal_service, "_get_linux_wifi_signal", return_value=90
    ) as mock_lin:
        with patch.object(signal_service, "_get_windows_wifi_signal") as mock_win:
            signal = signal_service._get_wifi_signal()
            assert signal == 90, "Signal level 90 was expected"
            mock_lin.assert_called_once()
            mock_win.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows specific test")
def test_get_windows_wifi_signal_parsing(signal_service: NetworkSignalService) -> None:
    """Тестує парсинг виводу команди netsh на Windows."""
    mock_output = "Interface name : Wi-Fi\nSignal : 85%\n"
    with patch("subprocess.check_output", return_value=mock_output):
        signal = signal_service._get_windows_wifi_signal()
        assert signal == 85, "Incorrect parsing of netsh signal percentage"


@pytest.mark.skipif(sys.platform == "win32", reason="Linux/Unix specific test")
def test_get_linux_wifi_signal_nmcli_parsing(
    signal_service: NetworkSignalService,
) -> None:
    """Тестує парсинг виводу команди nmcli на Linux."""
    mock_output = "no:SSID1:40\nyes:MyWiFi:92\n"
    with patch("subprocess.check_output", return_value=mock_output):
        signal = signal_service._get_linux_wifi_signal()
        assert signal == 92, "Incorrect parsing of nmcli output"


def test_connectivity_check(signal_service: NetworkSignalService) -> None:
    """Перевіряє логіку визначення наявності інтернет-з'єднання."""
    with patch("socket.create_connection") as mock_conn:
        mock_conn.return_value = MagicMock()
        assert signal_service._check_internet_connectivity() is True

        mock_conn.side_effect = TimeoutError()
        assert signal_service._check_internet_connectivity() is False, (
            "Should return False on TimeoutError"
        )


def test_get_signal_strength_flow(signal_service: NetworkSignalService) -> None:
    """Перевіряє пріоритети визначення сили сигналу (Wi-Fi vs Wired)."""
    with patch.object(signal_service, "_get_wifi_signal", return_value=75):
        assert signal_service.get_signal_strength() == 75, "Should return Wi-Fi signal"

    with patch.object(signal_service, "_get_wifi_signal", return_value=None):
        with patch.object(signal_service, "_has_wired_connection", return_value=True):
            assert signal_service.get_signal_strength() == 100, (
                "Should return 100 if there is a wired connection"
            )

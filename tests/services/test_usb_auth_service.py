"""Тести сервісу USB-авторизації."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import SECURITY_KEY_FILENAME, SECURITY_KEY_HASH
from app.services.usb_auth_service import UsbAuthService, UsbMonitorWorker


@pytest.fixture
def monitor_worker() -> UsbMonitorWorker:
    """Створює воркер з вимкненим циклом виконання."""
    worker = UsbMonitorWorker()
    worker.running = False
    return worker


def test_check_key_file_valid(monitor_worker: UsbMonitorWorker, tmp_path) -> None:
    """Перевірка валідації коректного файлу ключа."""
    mount_point = str(tmp_path)
    key_file = tmp_path / SECURITY_KEY_FILENAME

    # Мокаємо hashlib для стабільності тесту
    with patch("hashlib.sha256") as mock_hash:
        mock_hash.return_value.hexdigest.return_value = SECURITY_KEY_HASH
        key_file.write_text("dummy secret content")

        assert monitor_worker._check_key_file(mount_point) is True, (
            "Should return True for a valid key"
        )


def test_check_key_file_invalid_hash(
    monitor_worker: UsbMonitorWorker, tmp_path
) -> None:
    """Перевірка поведінки при невідповідності хешу файлу ключа."""
    mount_point = str(tmp_path)
    key_file = tmp_path / SECURITY_KEY_FILENAME
    key_file.write_text("wrong content")

    with patch("hashlib.sha256") as mock_hash:
        # Імітуємо невалідний хеш
        mock_hash.return_value.hexdigest.return_value = "wrong_hash"
        assert monitor_worker._check_key_file(mount_point) is False, (
            "Should return False for an invalid hash"
        )


def test_check_key_file_missing(monitor_worker: UsbMonitorWorker, tmp_path) -> None:
    """Перевірка поведінки при відсутності файлу ключа."""
    assert monitor_worker._check_key_file(str(tmp_path)) is False, (
        "Should return False if file is missing"
    )


def test_get_mounts_removable(monitor_worker: UsbMonitorWorker) -> None:
    """Перевірка виявлення знімних дисків."""
    mock_part = MagicMock()
    mock_part.opts = "rw,removable"
    mock_part.mountpoint = "/media/usb"

    with patch("psutil.disk_partitions", return_value=[mock_part]):
        mounts = monitor_worker._get_mounts()
        assert "/media/usb" in mounts, (
            "Worker should find the mount point of a removable disk"
        )


def test_auth_service_signal(qtbot) -> None:
    """Перевірка сигналу успішної авторизації."""
    service = UsbAuthService()

    with qtbot.waitSignal(service.auth_success_signal, timeout=1000) as blocker:
        service._handle_auth_success("/mnt/usb")

    assert blocker.args == ["/mnt/usb"], "Signal should contain the correct path"

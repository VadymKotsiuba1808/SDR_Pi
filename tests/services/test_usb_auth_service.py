"""
Тести для сервісу USB авторизації (UsbAuthService).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import SECURITY_KEY_FILENAME, SECURITY_KEY_HASH
from app.services.usb_auth_service import UsbAuthService, UsbMonitorWorker


@pytest.fixture
def monitor_worker():
    worker = UsbMonitorWorker()
    worker.running = False  # Не даємо циклу реально крутитися
    return worker


def test_check_key_file_valid(monitor_worker, tmp_path):
    """Тест перевірки валідного ключа."""
    # Створюємо файл з контентом, який відповідає хешу (нам потрібно знати контент)
    # Оскільки хеш у константах статичний, імітуємо співпадіння
    mount_point = str(tmp_path)
    key_file = tmp_path / SECURITY_KEY_FILENAME

    # Для тесту ми мокаємо hashlib, щоб не шукати реальний рядок під хеш
    with patch("hashlib.sha256") as mock_hash:
        mock_hash.return_value.hexdigest.return_value = SECURITY_KEY_HASH
        key_file.write_text("dummy secret content")

        assert monitor_worker._check_key_file(mount_point) is True


def test_check_key_file_invalid_hash(monitor_worker, tmp_path):
    """Тест перевірки файлу з неправильним хешем."""
    mount_point = str(tmp_path)
    key_file = tmp_path / SECURITY_KEY_FILENAME
    key_file.write_text("wrong content")

    with patch("hashlib.sha256") as mock_hash:
        mock_hash.return_value.hexdigest.return_value = "wrong_hash"
        assert monitor_worker._check_key_file(mount_point) is False


def test_check_key_file_missing(monitor_worker, tmp_path):
    """Тест відсутності файлу ключа."""
    assert monitor_worker._check_key_file(str(tmp_path)) is False


def test_get_mounts_removable(monitor_worker):
    """Тест виявлення знімних дисків через psutil."""
    mock_part = MagicMock()
    mock_part.opts = "rw,removable"
    mock_part.mountpoint = "/media/usb"

    with patch("psutil.disk_partitions", return_value=[mock_part]):
        mounts = monitor_worker._get_mounts()
        assert "/media/usb" in mounts


def test_auth_service_signal(qtbot):
    """Тест емісії сигналу фасадом UsbAuthService."""
    service = UsbAuthService()

    with qtbot.waitSignal(service.auth_success_signal, timeout=1000) as blocker:
        # Імітуємо успіх воркера
        service._handle_auth_success("/mnt/usb")

    assert blocker.args == ["/mnt/usb"]

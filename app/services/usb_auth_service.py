import os
import time
import hashlib
import psutil
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from app.core.constants import (
    SECURITY_KEY_FILENAME,
    SECURITY_KEY_HASH,
    USB_SCAN_INTERVAL_SECONDS,
)


class UsbMonitorWorker(QThread):
    """
    Воркер виконує брудну роботу в окремому потоці,
    щоб GUI на Raspberry Pi не фризило.
    """

    key_found = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self._known_devices = set()

    def run(self):
        self._known_devices = self._get_mounts()

        while self.running:
            current_devices = self._get_mounts()
            new_devices = current_devices - self._known_devices

            for mount_point in new_devices:
                if self._check_key_file(mount_point):
                    self.key_found.emit(mount_point)

            self._known_devices = current_devices
            time.sleep(USB_SCAN_INTERVAL_SECONDS)

    def _get_mounts(self) -> set:
        """Повертає множину точок монтування."""
        devices = set()
        try:
            for part in psutil.disk_partitions():
                # На Linux (Raspberry Pi) важливо фільтрувати, щоб не сканувати системні розділи
                if (
                    "removable" in part.opts
                    or "/media" in part.mountpoint
                    or "/mnt" in part.mountpoint
                ):
                    devices.add(part.mountpoint)
        except Exception as e:
            print(f"Error scanning disks: {e}")
        return devices

    def _check_key_file(self, mount_point: str) -> bool:
        """Перевіряє валідність файлу на диску."""
        print("Mount", mount_point)
        target_path = os.path.join(mount_point, SECURITY_KEY_FILENAME)
        print("Path", target_path)

        if not os.path.exists(target_path):
            return False

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                calculated_hash = hashlib.sha256(content.encode()).hexdigest()
                return calculated_hash == SECURITY_KEY_HASH
        except (OSError, IOError) as e:
            print(f"[USB Service] Помилка доступу (можливо, флешку витягнуто): {e}")
            return False
        return False

    def stop(self):
        self.running = False
        self.wait()


class UsbAuthService(QObject):
    """
    Фасад для роботи з сервісом.
    Головне вікно спілкується саме з цим класом.
    """

    auth_success_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._worker = UsbMonitorWorker()
        self._worker.key_found.connect(self._handle_auth_success)

    def start_monitoring(self):
        if not self._worker.isRunning():
            self._worker.start()

    def stop_monitoring(self):
        self._worker.stop()

    def _handle_auth_success(self, mount_point):
        print(f"Service: Auth token detected on {mount_point}")
        self.auth_success_signal.emit(mount_point)

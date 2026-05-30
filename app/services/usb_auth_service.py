import hashlib
import os
import time
from typing import Optional, Set

import psutil
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from app.core.constants import (
    SECURITY_KEY_FILENAME,
    SECURITY_KEY_HASH,
    USB_SCAN_INTERVAL_SECONDS,
)


class UsbMonitorWorker(QThread):
    """
    Воркер виконує моніторинг USB пристроїв в окремому потоці,
    щоб GUI на Raspberry Pi не фризило.
    """

    key_found = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.running: bool = True
        self._known_devices: Set[str] = set()

    def run(self) -> None:
        print("[USB Auth] Monitor worker started.")
        self._known_devices = self._get_mounts()

        while self.running:
            current_devices = self._get_mounts()

            new_devices = current_devices - self._known_devices

            if new_devices:
                print(f"[USB Auth] New devices detected: {new_devices}")

            for mount_point in new_devices:
                print(f"[USB Auth] Scanning device: {mount_point}...")
                if self._check_key_file(mount_point):
                    print(f"[USB Auth] VALID KEY FOUND at: {mount_point}")
                    self.key_found.emit(mount_point)
                else:
                    print(f"[USB Auth] No valid key at: {mount_point}")

            self._known_devices = current_devices
            time.sleep(USB_SCAN_INTERVAL_SECONDS)

        print("[USB Auth] Monitor worker stopped.")

    def _get_mounts(self) -> Set[str]:
        devices: Set[str] = set()
        try:
            for part in psutil.disk_partitions(all=False):
                # На Linux (Raspberry Pi) потрібно фільтрувати
                # Зазвичай флешки монтуються в /media або /mnt
                if (
                    "removable" in part.opts
                    or "/media" in part.mountpoint
                    or "/mnt" in part.mountpoint
                ):
                    devices.add(part.mountpoint)
        except Exception as e:
            print(f"[USB Auth] Error scanning disks: {e}")

        return devices

    def _check_key_file(self, mount_point: str) -> bool:
        target_path = os.path.join(mount_point, SECURITY_KEY_FILENAME)

        if not os.path.exists(target_path):
            return False

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                calculated_hash = hashlib.sha256(content.encode()).hexdigest()

                if calculated_hash == SECURITY_KEY_HASH:
                    return True
                else:
                    print(
                        f"[USB Auth] Security breach: File exists but hash mismatch at {mount_point}"
                    )
                    return False

        except (OSError, IOError) as e:
            print(f"[USB Auth] Access error (device removed?): {e}")
            return False

        return False

    def stop(self) -> None:
        self.running = False
        self.wait()


class UsbAuthService(QObject):
    """
    Фасад для роботи з сервісом.
    Головне вікно спілкується саме з цим класом.
    """

    auth_success_signal = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._worker = UsbMonitorWorker()
        self._worker.key_found.connect(self._handle_auth_success)
        print("[USB Auth] Service initialized.")

    def start_monitoring(self) -> None:
        if not self._worker.isRunning():
            self._worker.running = True
            self._worker.start()

    def stop_monitoring(self) -> None:
        if self._worker.isRunning():
            print("[USB Auth] Stopping monitoring...")
            self._worker.stop()

    def _handle_auth_success(self, mount_point: str) -> None:
        self.auth_success_signal.emit(mount_point)

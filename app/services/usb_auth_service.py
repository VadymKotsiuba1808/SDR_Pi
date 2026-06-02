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
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class UsbMonitorWorker(QThread):
    """
    ### Фоновий воркер для моніторингу USB-накопичувачів

    Періодично сканує точки монтування та перевіряє наявність валідного
    секретного ключа для авторизації.
    """

    key_found = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.running: bool = True
        self._known_devices: Set[str] = set()

    def run(self) -> None:
        logger.info("USB Monitor worker started")
        self._known_devices = self._get_mounts()

        while self.running:
            current_devices = self._get_mounts()
            new_devices = current_devices - self._known_devices

            if new_devices:
                logger.info(f"New USB devices detected: {new_devices}")

            for mount_point in new_devices:
                logger.debug(f"Scanning USB device: {mount_point}")
                if self._check_key_file(mount_point):
                    logger.info(f"Valid security key found at: {mount_point}")
                    self.key_found.emit(mount_point)
                else:
                    logger.debug(f"No security key at: {mount_point}")

            self._known_devices = current_devices
            time.sleep(USB_SCAN_INTERVAL_SECONDS)

        logger.info("USB Monitor worker stopped")

    def _get_mounts(self) -> Set[str]:
        """Отримує список точок монтування знімних носіїв."""
        devices: Set[str] = set()
        try:
            for part in psutil.disk_partitions(all=False):
                # Фільтрація USB-накопичувачів за прапорцем removable або шляхом монтування
                if (
                    "removable" in part.opts
                    or "/media" in part.mountpoint
                    or "/mnt" in part.mountpoint
                ):
                    devices.add(part.mountpoint)
        except Exception as e:
            logger.error(f"Error scanning disks: {e}")

        return devices

    def _check_key_file(self, mount_point: str) -> bool:
        """Перевіряє SHA-256 хеш файлу ключа на пристрої."""
        target_path = os.path.join(mount_point, SECURITY_KEY_FILENAME)

        if not os.path.exists(target_path):
            return False

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                calculated_hash = hashlib.sha256(content.encode()).hexdigest()

                if calculated_hash == SECURITY_KEY_HASH:
                    return True

                logger.warning(f"Security breach: Hash mismatch at {mount_point}")
                return False

        except (OSError, IOError) as e:
            logger.debug(f"Access error (device removed?): {e}")
            return False

        return False

    def stop(self) -> None:
        """Зупиняє воркер та очікує завершення потоку."""
        self.running = False
        self.wait()


class UsbAuthService(QObject):
    """
    ### Сервіс апаратної авторизації через USB-ключ

    Керує фоновим моніторингом та сповіщає систему про успішну
    авторизацію при підключенні фізичного ключа.
    """

    auth_success_signal = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._worker = UsbMonitorWorker()
        self._worker.key_found.connect(self._handle_auth_success)
        logger.info("USB Auth Service initialized")

    def start_monitoring(self) -> None:
        if not self._worker.isRunning():
            self._worker.running = True
            self._worker.start()

    def stop_monitoring(self) -> None:
        if self._worker.isRunning():
            logger.info("Stopping USB monitoring...")
            self._worker.stop()

    def _handle_auth_success(self, mount_point: str) -> None:
        self.auth_success_signal.emit(mount_point)

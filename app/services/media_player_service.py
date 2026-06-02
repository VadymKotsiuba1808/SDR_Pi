import os
import shutil
from typing import Optional

from PyQt6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)

from app.core.logging_config import get_logger
from app.protocols import OSService

logger = get_logger(__name__)


class MediaPlayerService(QObject):
    """
    Сервіс керування зовнішнім медіа-плеєром (VLC).

    Забезпечує ізольований запуск VLC для перегляду медіа-файлів,
    автоматично очищаючи змінні середовища Qt для уникнення конфліктів
    між основною програмою та плеєром.

    Attributes:
        playback_finished (pyqtSignal): Сигнал, що випромінюється при закритті плеєра.
        error_occurred (pyqtSignal): Сигнал з повідомленням про помилку (str).
    """

    playback_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, system: OSService, parent: Optional[QObject] = None) -> None:
        """Ініціалізує сервіс медіа-плеєра."""
        super().__init__(parent)
        self.system_service = system
        self._process: Optional[QProcess] = None
        self._vlc_path: Optional[str] = self._get_vlc_executable()

    def play(self, file_path: str) -> None:
        """Запускає відтворення медіа-файлу у зовнішньому вікні VLC."""
        if not self._vlc_path:
            self.error_occurred.emit("VLC плеєр не знайдено в системі.")
            return

        if not os.path.exists(file_path):
            self.error_occurred.emit(f"Файл не знайдено: {file_path}")
            return

        self.stop()

        self._process = QProcess(self)
        self._process.setProcessEnvironment(self._prepare_environment())

        # Базові аргументи для VLC
        args = [
            "--fullscreen",
            "--play-and-pause",
            "--image-duration=-1",
            "--no-qt-privacy-ask",
            "--no-qt-error-dialogs",
            "--global-key-quit=q",
            "--loop",
        ]

        # Специфічні налаштування для різних ОС
        if self.system_service.is_linux:
            # Використовуємо xcb_x11 для стабільності на Raspberry Pi/Linux
            args.append("--vout=xcb_x11")
            args.append(file_path)
        elif self.system_service.is_windows:
            # Windows краще обробляє шляхи через QUrl
            url = QUrl.fromLocalFile(file_path)
            args.append(url.toString())

        self._process.finished.connect(self._on_process_finished)
        self._process.readyReadStandardError.connect(self._handle_stderr)

        self._process.start(self._vlc_path, args)

    def stop(self) -> None:
        """Примусово зупиняє процес відтворення."""
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.close()
            self._process = None

    def _prepare_environment(self) -> QProcessEnvironment:
        """Готує чисте середовище для запуску VLC (очищення QT_* змінних)."""
        env = QProcessEnvironment.systemEnvironment()

        # Список критичних змінних, що викликають сегфолти при конфлікті версій
        keys_to_clean = [
            "QT_PLUGIN_PATH",
            "QT_QPA_PLATFORM_PLUGIN_PATH",
            "LD_LIBRARY_PATH",
            "PYTHONPATH",
            "PYTHONHOME",
        ]

        for key in keys_to_clean:
            if env.contains(key):
                env.remove(key)

        # Додатково видаляємо будь-які інші QT_ змінні для повної ізоляції
        for key in env.keys():
            if key.startswith("QT_"):
                env.remove(key)

        return env

    @pyqtSlot()
    def _on_process_finished(self) -> None:
        """Обробник завершення процесу VLC."""
        self.playback_finished.emit()
        self._process = None

    @pyqtSlot()
    def _handle_stderr(self) -> None:
        """Зчитує та логує помилки з виводу VLC."""
        if self._process:
            data = self._process.readAllStandardError().data().decode().strip()
            if data:
                logger.debug(f"[VLC Log]: {data}")

    def _get_vlc_executable(self) -> Optional[str]:
        """Визначає шлях до виконуваного файлу VLC."""
        if self.system_service.is_windows:
            possible_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path

        # Для Linux або якщо не знайдено за стандартними шляхами Windows
        return shutil.which("vlc")

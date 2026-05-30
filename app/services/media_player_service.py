"""
Сервіс для керування зовнішнім медіа-плеєром (VLC).
Відповідає за запуск процесу, очищення змінних середовища та обробку помилок.
"""

import os
import shutil

from PyQt6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)

from app.protocols import OSService


class MediaPlayerService(QObject):

    # Сигнали для зворотного зв'язку з UI
    playback_finished = pyqtSignal()  # Відео завершилось або вікно закрили
    error_occurred = pyqtSignal(str)  # Щось пішло не так

    def __init__(self, system: OSService, parent=None):
        super().__init__(parent)
        self.system_service = system

        self._setup_state_variables()

    def _setup_state_variables(self):
        self._process = None
        self._vlc_path = self._get_vlc_executable()

    def play(self, file_path: str):
        """Запускає відео у зовнішньому плеєрі."""

        print(file_path)

        if not self._vlc_path:
            self.error_occurred.emit("VLC плеєр не знайдено в системі.")
            return

        if not os.path.exists(file_path):
            self.error_occurred.emit(f"Файл не знайдено: {file_path}")
            return

        self.stop()

        self._process = QProcess(self)

        env = QProcessEnvironment.systemEnvironment()
        # Видаляємо змінні Qt, щоб VLC (який теж на Qt) не конфліктував з нашою програмою
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

        for key in env.keys():
            if key.startswith("QT_"):
                env.remove(key)

        self._process.setProcessEnvironment(env)

        args = [
            "--fullscreen",
            "--play-and-pause",
            "--image-duration=-1",
            "--no-qt-privacy-ask",
            "--no-qt-error-dialogs",
            "--global-key-quit=q",
            "--loop",
        ]

        # Для Linux додаємо специфічний відео-вихід
        if self.system_service.is_linux:
            args.append("--vout=xcb_x11")
            args.append(file_path)
        elif self.system_service.is_windows:
            url = QUrl.fromLocalFile(file_path)
            args.append(url.toString())

        # Підписка на події процесу
        self._process.finished.connect(self._on_process_finished)
        self._process.readyReadStandardError.connect(self._handle_stderr)

        print(f"[MediaPlayer] Запуск: {self._vlc_path} {file_path}")
        self._process.start(self._vlc_path, args)

    def stop(self):
        """Примусово зупиняє відтворення."""
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            print("[MediaPlayer] Зупинка процесу...")
            self._process.close()
            self._process = None

    @pyqtSlot()
    def _on_process_finished(self):
        print("[MediaPlayer] Відтворення завершено.")
        self.playback_finished.emit()
        self._process = None

    @pyqtSlot()
    def _handle_stderr(self):
        if self._process:
            data = self._process.readAllStandardError().data().decode().strip()
            if data:
                print(f"[VLC Log]: {data}")

    def _get_vlc_executable(self):
        """
        Знаходить шлях до виконуваного файлу VLC в залежності від ОС.
        """

        if self.system_service.is_windows:
            # Шукаємо у стандартних папках Windows
            possible_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path

            # Якщо не знайшли, шукаємо в системному PATH
            path_in_env = shutil.which("vlc")
            if path_in_env:
                return path_in_env

        elif self.system_service.is_linux:
            path_in_env = shutil.which("vlc")
            if path_in_env:
                return path_in_env

        # Якщо нічого не знайшли
        return None

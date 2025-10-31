from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from vidgear.gears import ScreenGear, WriteGear
import time


class RecordingService(QObject):
    # Сигнали, які ми будемо відправляти у MainWindow
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_error = pyqtSignal(str)  # Сигнал для помилок

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.writer = None
        self.screen_gear = None
        self.stream = None

        # Власний QTimer менеджера
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._record_frame)
        self.fps = 20

    def start_recording(self, output_filename):
        if self.is_recording:
            return

        try:
            # Налаштування запису
            output_params = {"-vcodec": "libx264", "-crf": 20, "-preset": "ultrafast"}
            self.writer = WriteGear(
                output=output_filename, logging=True, **output_params
            )

            # Налаштування захоплення (monitor=1 це головний монітор)
            self.screen_gear = ScreenGear(monitor=1)
            self.stream = self.screen_gear.start()

            # Запускаємо таймер
            self.timer.start(1000 // self.fps)
            self.is_recording = True
            self.recording_started.emit()  # Повідомляємо MainWindow
            print(f"Запис розпочато... {output_filename}")

        except Exception as e:
            self.recording_error.emit(f"Помилка при запуску: {e}")
            self.stop_recording()

    def _record_frame(self):
        # Цей метод викликається таймером
        if not self.is_recording or self.stream is None:
            return

        frame = self.stream.read()
        if frame is not None:
            self.writer.write(frame)
        else:
            # Якщо потік завершився (наприклад, закрили вікно)
            self.stop_recording()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.timer.stop()

        # Чистимо ресурси
        if self.screen_gear:
            self.screen_gear.stop()
            self.screen_gear = None
        if self.writer:
            self.writer.close()
            self.writer = None

        self.stream = None
        self.recording_stopped.emit()  # Повідомляємо MainWindow
        print("Запис зупинено.")

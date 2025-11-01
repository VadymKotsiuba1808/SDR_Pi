from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot, QTime
from vidgear.gears import ScreenGear, WriteGear


class RecordingService(QObject):
    # Сигнали, які ми будемо відправляти у MainWindow
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_error = pyqtSignal(str)

    # НОВІ СИГНАЛИ
    recording_paused = pyqtSignal(bool)  # true = on pause, false = resumed
    duration_updated = pyqtSignal(str)  # Будемо відправляти час у форматі "HH:MM:SS"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.is_paused = False

        self.writer = None
        self.screen_gear = None
        self.stream = None

        self.fps = 20

        # Таймер для захоплення кадрів
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._record_frame)

        # НОВИЙ ТАЙМЕР: для підрахунку тривалості
        self.duration_timer = QTimer(self)
        self.duration_timer.timeout.connect(self._update_duration)
        self.start_time = QTime()  # Для підрахунку часу

    def start_recording(self, output_filename):
        if self.is_recording:
            return

        try:
            output_params = {"-vcodec": "libx264", "-crf": 20, "-preset": "ultrafast"}
            self.writer = WriteGear(
                output=output_filename, logging=True, **output_params
            )

            self.screen_gear = ScreenGear(monitor=1)
            self.stream = self.screen_gear.start()

            # Запускаємо обидва таймери
            self.frame_timer.start(1000 // self.fps)
            self.duration_timer.start(1000)  # Оновлення кожну секунду

            self.start_time.start()  # Скидаємо лічильник
            self.is_recording = True
            self.is_paused = False

            self.recording_started.emit()
            print(f"Запис розпочато... {output_filename}")

        except Exception as e:
            self.recording_error.emit(f"Помилка при запуску: {e}")
            self.stop_recording()

    def _record_frame(self):
        # Цей метод викликається frame_timer
        if not self.is_recording or self.is_paused or self.stream is None:
            return

        frame = self.stream.read()
        if frame is not None:
            self.writer.write(frame)
        else:
            self.stop_recording()

    def _update_duration(self):
        # Цей метод викликається duration_timer
        if not self.is_recording or self.is_paused:
            return

        # Рахуємо час, що минув
        elapsed_ms = self.start_time.elapsed()
        seconds = elapsed_ms // 1000

        # Форматуємо у "HH:MM:SS"
        hours = (seconds / 60) // 60
        minutes = seconds // 60
        seconds = seconds % 60
        self.duration_updated.emit(f"{hours:02}:{minutes:02}:{seconds:02}")

    @pyqtSlot()  # Робимо це публічним слотом
    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.is_paused = False

        # Зупиняємо таймери
        self.frame_timer.stop()
        self.duration_timer.stop()

        if self.screen_gear:
            self.screen_gear.stop()
            self.screen_gear = None
        if self.writer:
            self.writer.close()
            self.writer = None

        self.stream = None
        self.recording_stopped.emit()
        self.duration_updated.emit("00:00:00")  # Скидаємо лічильник
        print("Запис зупинено.")

    @pyqtSlot(bool)  # Публічний слот, який приймає стан кнопки "пауза"
    def toggle_pause(self, is_paused):
        if not self.is_recording:
            return

        self.is_paused = is_paused

        if self.is_paused:
            # Не зупиняємо frame_timer, просто ігноруємо кадри
            # self.frame_timer.stop() # Або так, якщо хочете економити ресурси
            print("Запис на паузі")
        else:
            # self.frame_timer.start()
            # Перезапускаємо лічильник часу, щоб він не враховував паузу
            # Це складно. Простіше: не зупиняти duration_timer,
            # а просто _update_duration буде повертати return, якщо is_paused
            print("Запис відновлено")

        self.recording_paused.emit(self.is_paused)

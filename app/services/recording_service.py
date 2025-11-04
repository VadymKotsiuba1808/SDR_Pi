from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QElapsedTimer
from vidgear.gears import WriteGear
import mss
import numpy as np
import time
import platform


class RecordingService(QThread):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_error = pyqtSignal(str)
    recording_paused = pyqtSignal(bool)
    duration_updated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._setup_state_variables()

    def _setup_state_variables(self):
        self.is_running = False
        self.is_paused = False

        self.filename = ""
        self.fps = 35
        self.video_quality_crf = 26

        if platform.system() == "Windows":
            self.pix_fmt = "bgra"
        else:
            self.pix_fmt = "rgb24"

        self.start_time = QElapsedTimer()

    def run(self):
        print(f"[Recorder] Потік запущено... {self.thread()}")
        self.is_running = True

        try:
            # --- Ініціалізація у фоновому потоці ---
            self.sct = mss.mss()
            self.monitor = self.sct.monitors[1]
            width = self.monitor["width"]
            height = self.monitor["height"]

            all_params = {
                # "-vcodec": "libx264",  # Кодек для вихідного файлу
                # "-crf": str(
                #     self.video_quality_crf
                # ),  # Рівень якості (менше = краща якість)
                # "-preset": "faster",  # Швидкість кодування
                # "-pix_fmt": self.pix_fmt,  # Формат пікселів для сумісності
                # "-r": str(self.fps),  # Частота кадрів
                # "-s": f"{width}x{height}",  # Розмір кадру
                "-input_framerate": str(self.fps),
                "-input_pixfmt": self.pix_fmt,  # 'bgra' (Win) або 'rgb24' (Lin)
                # --- Стандартні ключі FFmpeg для ВИХОДУ ---
                "-vcodec": "libx264",
                "-crf": str(self.video_quality_crf),
                "-preset": "faster",
                "-pix_fmt": "yuv420p",
                "-s": f"{width}x{height}",
            }

            self.writer = WriteGear(
                output=self.filename,
                logging=False,
                **all_params,
            )

            self.start_time.start()
            self.prev_total_ms = 0
            self.dif_time_ms = 0
            self.pause_start = 0
            self.recording_started.emit()
            print(f"Запис розпочато... {self.filename}")

            # --- ГОЛОВНИЙ ЦИКЛ ЗАПИСУ ---
            while self.is_running:
                if not self.is_paused:
                    start = time.time()

                    sct_img = self.sct.grab(self.monitor)
                    frame = np.array(sct_img)
                    if frame is not None:
                        self.writer.write(frame)
                        self.update_duration()

                    # реальна затримка, що враховує час обробки кадру
                    elapsed = time.time() - start
                    sleep_time = max(0, (1 / self.fps) - elapsed)
                    # time.sleep(sleep_time)
                    self.msleep(int(sleep_time * 1000))

            print("Цикл запису завершено.")

        except Exception as e:
            print(f"[Recorder] Критична помилка у потоці: {e}")
            self.recording_error.emit(str(e))

        finally:
            if self.sct:
                self.sct.close()
                self.sct = None
            if self.writer:
                self.writer.close()
                self.writer = None

            self.recording_stopped.emit()
            self.duration_updated.emit("00:00:00")
            print("Ресурси запису очищено. Потік зупинено.")

    def update_duration(self):
        if self.is_paused:
            return

        total_ms = self.start_time.elapsed() - self.dif_time_ms

        # оновлюємо раз на секунду
        if total_ms - self.prev_total_ms < 1000:
            return

        self.prev_total_ms = total_ms

        total_seconds = total_ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        self.duration_updated.emit(f"{hours:02}:{minutes:02}:{seconds:02}")

    @pyqtSlot(str)
    def start_recording(self, filename):
        # Це НЕ запускає запис, це запускає потік
        if not self.isRunning():
            self.filename = filename
            self.start()
        else:
            print("[Recorder] Помилка: потік вже запущено.")

    @pyqtSlot()
    def stop_recording(self):
        print("[Recorder] Отримано команду stop_recording.")
        self.is_running = False

    @pyqtSlot(bool)
    def toggle_pause(self, is_paused):
        if is_paused and not self.is_paused:
            self.pause_start = self.start_time.elapsed()
        elif not is_paused and self.is_paused:
            paused_for = self.start_time.elapsed() - self.pause_start
            self.dif_time_ms += paused_for
            self.pause_start = 0

        self.is_paused = is_paused
        self.recording_paused.emit(self.is_paused)
        print(f"Запис на паузі: {is_paused}")

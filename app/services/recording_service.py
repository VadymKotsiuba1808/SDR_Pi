from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QElapsedTimer
from vidgear.gears import WriteGear
import mss
import numpy as np
import time  # Нам потрібен time.sleep


class RecordingService(QThread):  # Змінено QObject на QThread
    # Сигнали тепер визначаються тут
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_error = pyqtSignal(str)
    recording_paused = pyqtSignal(bool)
    duration_updated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Прапорці для керування потоком
        self.is_running = False  # Замість is_recording
        self.is_paused = False

        # Вхідні дані
        self._filename = ""
        self.fps = 20

        # Внутрішні об'єкти (будуть створені у run())
        self.sct = None
        self.writer = None
        self.monitor = None

        self.prev_total_ms = None
        self.dif_time_ms = None
        self.pause_start = None
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

            # --- ЗМІНЕНО: Налаштування параметрів ---

            # Створюємо ОДИН СЛОВНИК
            # vidgear передасть це все в командний рядок ffmpeg

            all_params = {
                "-vcodec": "libx264",  # Кодек для вихідного файлу
                "-crf": "20",  # Рівень якості (менше = краща якість)
                "-preset": "ultrafast",  # Швидкість кодування
                "-pix_fmt": "yuv420p",  # Формат пікселів для сумісності
                "-r": str(self.fps),  # Частота кадрів
                "-s": f"{width}x{height}",  # Розмір кадру
            }

            # 3. Викликаємо WriteGear, передаючи ТІЛЬКИ **kwargs
            self.writer = WriteGear(
                output=self._filename,
                logging=True,
                **all_params,  # <--- Передаємо всі параметри як один розпакований словник
            )
            # ----------------------------------------

            self.start_time.start()
            self.prev_total_ms = 0
            self.dif_time_ms = 0
            self.pause_start = 0
            self.recording_started.emit()
            print(f"Запис розпочато... {self._filename}")

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
            # (Блок finally без змін)
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

    # --- СЛОТИ КЕРУВАННЯ (будуть викликані з GUI) ---

    @pyqtSlot(str)
    def start_recording(self, filename):
        # Це НЕ запускає запис, це запускає потік
        if not self.isRunning():
            self._filename = filename
            self.start()  # Це запускає метод run()
        else:
            print("[Recorder] Помилка: потік вже запущено.")

    @pyqtSlot()
    def stop_recording(self):
        # Це просто встановлює прапорець. Цикл run() зупиниться сам
        print("[Recorder] Отримано команду stop_recording.")
        self.is_running = False

    @pyqtSlot(bool)
    def toggle_pause(self, is_paused):
        # змінюємо стан
        if is_paused and not self.is_paused:
            # користувач натиснув "Пауза"
            self.pause_start = self.start_time.elapsed()
        elif not is_paused and self.is_paused:
            # користувач зняв "Пауза"
            paused_for = self.start_time.elapsed() - self.pause_start
            self.dif_time_ms += paused_for
            self.pause_start = 0

        self.is_paused = is_paused
        self.recording_paused.emit(self.is_paused)
        print(f"Запис на паузі: {is_paused}")

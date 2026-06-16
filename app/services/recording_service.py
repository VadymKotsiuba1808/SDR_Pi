import time
from typing import Any, Optional

import cv2
import mss
import numpy as np
from PyQt6.QtCore import QElapsedTimer, QThread, pyqtSignal, pyqtSlot
from vidgear.gears import WriteGear

from app.core.logging_config import get_logger
from app.protocols import OSService

logger = get_logger(__name__)


class RecordingService(QThread):
    """
    ### Сервіс фонового запису екрану

    Забезпечує захоплення відеопотоку та його збереження у форматі `.mp4`
    з використанням апаратного або програмного кодування.
    """

    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_error = pyqtSignal(str)
    recording_paused = pyqtSignal(bool)
    duration_updated = pyqtSignal(str)

    def __init__(self, system: OSService, parent=None):
        super().__init__(parent)
        self.system_service = system
        self._setup_state_variables()

    def _setup_state_variables(self) -> None:
        self.is_running = False
        self.is_paused = False
        self.filename = ""

        self.prev_total_ms = 0
        self.dif_time_ms = 0
        self.pause_start = 0

        if self.system_service.is_windows:
            self.fps = 30
            self.monitor_index = 1
            self.scale_factor = 1.0
        else:
            self.fps = 10
            self.monitor_index = 0
            self.scale_factor = 0.5

        self.start_time = QElapsedTimer()
        self.sct: Optional[Any] = None
        self.writer: Optional[WriteGear] = None

        self.frame_duration = 1.0 / self.fps

    def _get_ffmpeg_params(
        self, width: int, height: int, use_hardware: bool = False
    ) -> dict:
        """Повертає оптимізовані параметри FFmpeg для кодування відео."""
        params = {
            "-input_framerate": str(self.fps),
            "-s": f"{width}x{height}",
            "-pix_fmt": "yuv420p",
            "-thread_queue_size": "512",
            "-r": str(self.fps),
        }

        if self.system_service.is_windows:
            params.update(
                {
                    "-vcodec": "libx264",
                    "-preset": "ultrafast",
                    "-crf": "25",
                }
            )
        else:
            if use_hardware:
                # Апаратне кодування для Raspberry Pi (V4L2)
                params.update(
                    {
                        "-vcodec": "h264_v4l2m2m",
                        "-b:v": "1000k",
                        "-bufsize": "2000k",
                        "-g": str(self.fps * 2),
                    }
                )
            else:
                # Програмне кодування з низьким навантаженням на CPU
                params.update(
                    {
                        "-vcodec": "libx264",
                        "-preset": "ultrafast",
                        "-tune": "zerolatency",
                        "-crf": "35",
                        "-threads": "4",
                        "-g": str(self.fps),
                        "-maxrate": "1500k",
                        "-bufsize": "3000k",
                    }
                )

        return params

    def run(self) -> None:
        logger.info("Recording thread started")
        self.is_running = True

        try:
            self.sct = mss.mss()
            if len(self.sct.monitors) > self.monitor_index:
                monitor = self.sct.monitors[self.monitor_index]
            else:
                monitor = self.sct.monitors[1]

            raw_width = monitor["width"]
            raw_height = monitor["height"]

            self.record_width = int(raw_width * self.scale_factor)
            self.record_height = int(raw_height * self.scale_factor)

            # FFmpeg вимагає парні значення ширини/висоти для багатьох кодеків
            if self.record_width % 2 != 0:
                self.record_width -= 1
            if self.record_height % 2 != 0:
                self.record_height -= 1

            logger.info(
                "Scaling: %dx%d -> %dx%d",
                raw_width,
                raw_height,
                self.record_width,
                self.record_height,
            )

        except Exception as e:
            self.recording_error.emit(f"MSS init failed: {e}")
            return

        self.writer = None

        if not self.system_service.is_windows:
            try:
                logger.info("Attempting Hardware Encoding...")
                params = self._get_ffmpeg_params(
                    self.record_width, self.record_height, use_hardware=True
                )
                self.writer = WriteGear(
                    output=self.filename, logging=False, output_params=params
                )
            except Exception as e:
                logger.warning(
                    "Hardware encoding failed: %s. Switching to Software.", e
                )
                self.writer = None

        if self.writer is None:
            try:
                logger.info("Using Software Encoding (libx264 ultrafast)...")
                params = self._get_ffmpeg_params(
                    self.record_width, self.record_height, use_hardware=False
                )
                self.writer = WriteGear(
                    output=self.filename, logging=False, output_params=params
                )
            except Exception as e:
                self.recording_error.emit(f"Writer Init Critical Error: {e}")
                self.is_running = False
                return

        self.start_time.start()
        self.recording_started.emit()

        self.frames_written = 0
        self.start_time_perf = time.perf_counter()

        try:
            while self.is_running:
                if self.is_paused:
                    time.sleep(0.1)
                    # Коригуємо час початку після паузи
                    self.start_time_perf += 0.1
                    continue

                self.update_duration()

                sct_img = self.sct.grab(monitor)
                frame = np.array(sct_img)
                frame = frame[:, :, :3]

                if self.scale_factor != 1.0:
                    frame = cv2.resize(
                        frame,
                        (self.record_width, self.record_height),
                        interpolation=cv2.INTER_NEAREST,
                    )

                if self.writer:
                    self.writer.write(frame)
                    self.frames_written += 1

                    # Алгоритм компенсації FPS: дублюємо кадр, якщо захоплення відстає від таймера
                    elapsed = time.perf_counter() - self.start_time_perf
                    expected_frames = int(elapsed * self.fps)

                    if expected_frames > self.frames_written + 1:
                        self.writer.write(frame)
                        self.frames_written += 1

                # Динамічна пауза для плавності кадрів
                next_frame_time = self.start_time_perf + (
                    self.frames_written / self.fps
                )
                sleep_time = next_frame_time - time.perf_counter()

                if sleep_time > 0.001:
                    time.sleep(sleep_time)

        except Exception as e:
            self.recording_error.emit(f"Loop Error: {e}")
            logger.error("Recording loop error: %s", e)

        finally:
            logger.info("Stopping recorder...")
            if self.sct:
                self.sct.close()
            if self.writer:
                self.writer.close()

            self.recording_stopped.emit()
            self.duration_updated.emit("00:00:00")

    def update_duration(self) -> None:
        """Оновлює та емітує поточну тривалість запису."""
        if self.is_paused:
            return
        total_ms = self.start_time.elapsed() - self.dif_time_ms

        if total_ms - self.prev_total_ms >= 1000:
            self.prev_total_ms = total_ms
            total_seconds = total_ms // 1000
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            self.duration_updated.emit(f"{h:02}:{m:02}:{s:02}")

    @pyqtSlot(str)
    def start_recording(self, filename: str) -> None:
        if not self.isRunning():
            self.filename = filename
            self.start()

    @pyqtSlot()
    def stop_recording(self) -> None:
        self.is_running = False

    @pyqtSlot(bool)
    def toggle_pause(self, is_paused: bool) -> None:
        if is_paused and not self.is_paused:
            self.pause_start = self.start_time.elapsed()
        elif not is_paused and self.is_paused:
            self.dif_time_ms += self.start_time.elapsed() - self.pause_start
        self.is_paused = is_paused
        self.recording_paused.emit(self.is_paused)

import math
import random
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import numpy as np
from PyQt6.QtCore import (
    QCoreApplication,
    QObject,
    QTimer,
    pyqtSlot,
)

from app.core.constants import DB_OFFSET, UINT8_MAX, UINT8_MIN
from app.models.detection_object import DetectionObject
from app.models.gps_data import GPSData
from app.models.service_response import DbOperation, ServiceResponse
from temp.pi_server_service import PiServerService

# --- КОНФІГУРАЦІЯ СИМУЛЯЦІЇ ---
SIMULATION_RADIUS_METERS = 85000  # 85 км
MAX_SIMULTANEOUS_TARGETS = 15  # Макс цілей
UPDATE_INTERVAL_MS = 300  # Оновлення фізики (3.3 Гц)
STREAM_INTERVAL_MS = 50  # Оновлення "живого" потоку (20 Гц)

# Інтервал відправки фону для КОЖНОГО об'єкта (2 хвилини)
TARGET_BG_INTERVAL_SEC = 120

SPEED_MULTIPLIER = 2.0


class SimulatedTarget:
    """
    Клас фізичної симуляції однієї цілі.
    """

    def __init__(self, template: DetectionObject):
        self.id = str(uuid.uuid4())
        self.template = template
        self.name = template.name
        self.object_class = template.object_class
        self.is_dangerous = template.is_dangerous

        self.base_freq = self._parse_frequency(template.rf_params_hz)
        self.current_freq = self.base_freq

        angle_deg = random.uniform(0, 360)
        dist_m = random.uniform(
            SIMULATION_RADIUS_METERS * 0.4, SIMULATION_RADIUS_METERS
        )

        self.x = dist_m * math.cos(math.radians(angle_deg))
        self.y = dist_m * math.sin(math.radians(angle_deg))

        base_speed_ms = 25.0
        name_lower = self.name.lower()
        if "mavic" in name_lower or "matrice" in name_lower:
            base_speed_ms = random.uniform(12, 18)
        elif "shahed" in name_lower or "geran" in name_lower:
            base_speed_ms = random.uniform(45, 60)
        elif "lancet" in name_lower:
            base_speed_ms = random.uniform(30, 45)
        elif "bird" in name_lower:
            base_speed_ms = random.uniform(10, 15)

        self.speed = base_speed_ms * SPEED_MULTIPLIER

        angle_to_center = (angle_deg + 180) % 360
        move_angle = angle_to_center + random.uniform(-60, 60)

        self.vx = self.speed * math.cos(math.radians(move_angle))
        self.vy = self.speed * math.sin(math.radians(move_angle))

        self.behavior = random.choice(["linear", "linear", "circle", "zigzag"])

        self.confidence = random.uniform(0.6, 1.0)
        self.is_hidden = False
        self.hidden_until = 0.0

        self.last_bg_time = 0.0
        self.force_bg_send = True

    def _parse_frequency(self, params: List[str]) -> float:
        if not params:
            return random.uniform(400e6, 6000e6)
        raw_str = random.choice(params)
        if "-" in raw_str:
            try:
                parts = raw_str.split("-")
                f_min = float(parts[0])
                f_max = float(parts[1])
                return random.uniform(f_min, f_max)
            except ValueError:
                return 900e6
        else:
            try:
                return float(raw_str)
            except ValueError:
                return 900e6

    def update(self, dt: float) -> bool:
        now = time.time()
        if self.is_hidden:
            if now > self.hidden_until:
                self.is_hidden = False
                self.confidence = random.uniform(0.5, 0.8)
        else:
            if random.random() < 0.008:
                self.is_hidden = True
                self.hidden_until = now + random.uniform(1.5, 4.0)

        if self.name.upper() == "DJI MAVIC 3":
            return True

        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.behavior == "circle":
            turn_rate = 0.3 * dt
            new_vx = self.vx * math.cos(turn_rate) - self.vy * math.sin(turn_rate)
            new_vy = self.vx * math.sin(turn_rate) + self.vy * math.cos(turn_rate)
            self.vx, self.vy = new_vx, new_vy

        elif self.behavior == "zigzag":
            if random.random() < 0.05:
                change = random.uniform(-0.5, 0.5)
                new_vx = self.vx * math.cos(change) - self.vy * math.sin(change)
                new_vy = self.vx * math.sin(change) + self.vy * math.cos(change)
                self.vx, self.vy = new_vx, new_vy

        self.current_freq = self.base_freq + random.uniform(-150, 150)

        dist_sq = self.x**2 + self.y**2
        if dist_sq > (SIMULATION_RADIUS_METERS * 1.1) ** 2:
            return False

        return True

    def get_event_data(self) -> Optional[Dict[str, Any]]:
        if self.is_hidden:
            return None

        dist_m = math.sqrt(self.x**2 + self.y**2)
        angle_rad = math.atan2(self.y, self.x)
        angle_deg = (math.degrees(angle_rad) + 360) % 360
        det_type = "Sound" if self.current_freq < 20000 else "RF"

        return {
            "id": self.id,
            "type": det_type,
            "name": self.name,
            "object_class": self.object_class,
            "confidence": round(self.confidence, 3),
            "timestamp": datetime.now().isoformat(),
            "distance_km": round(dist_m / 1000.0, 4),
            "angle": round(angle_deg, 2),
            "frequency_hz": int(self.current_freq),
            "is_dangerous": self.is_dangerous,
        }

    def check_and_get_background(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        if self.force_bg_send or (now - self.last_bg_time > TARGET_BG_INTERVAL_SEC):
            self.last_bg_time = now
            self.force_bg_send = False

            fft_size = 512
            rows = 100
            noise_level = -105.0
            noise = np.random.normal(0, 2.0, (rows, fft_size)) + noise_level
            center_col = fft_size // 2
            for r in range(rows):
                drift = int(np.sin(r * 0.1) * 3)
                c = center_col + drift
                if 0 <= c < fft_size:
                    noise[r, max(0, c - 2) : min(fft_size, c + 3)] += 20.0

            data_uint8 = (noise + DB_OFFSET).clip(UINT8_MIN, UINT8_MAX).astype(np.uint8)

            return {
                "id": self.id,
                "timestamp": datetime.now().isoformat(),
                "spectral_data": {
                    "center_freq_hz": self.base_freq,
                    "sample_rate_hz": 20_000_000.0,
                    "duration_sec": 5.0,
                    "data_magnitude": data_uint8.tolist(),
                },
            }
        return None


class AdvancedNetworkUtility(PiServerService):
    """
    Симуляційний сервер, що наслідує PiServerService.
    """

    def __init__(self, port: int = 6000, parent: Optional[QObject] = None):
        super().__init__(port=port, parent=parent)
        print("[SimServer] Initializing advanced simulation...")

        # --- SIMULATION STATE ---
        self.active_targets: List[SimulatedTarget] = []
        self.detection_templates: List[DetectionObject] = []
        self.session_blacklist: Set[str] = set()

        # GPS Base coords
        self.gps_lat = 50.18
        self.gps_lon = 27.06

        # --- TIMERS ---
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._on_sim_tick)
        self.sim_timer.setInterval(UPDATE_INTERVAL_MS)

        self.stream_timer = QTimer(self)
        self.stream_timer.timeout.connect(self._on_stream_tick)
        self.stream_timer.setInterval(STREAM_INTERVAL_MS)

        self.is_rf_streaming = False
        self.is_sound_streaming = False

        self._setup_sim_signals()

    def _setup_sim_signals(self):
        # Підключаємось до результатів БД, щоб оновлювати шаблони
        self.db.request_finished.connect(self._on_db_response)

    def start(self):
        # Початкове завантаження шаблонів
        self.db.request_all_objects()
        super().start()
        self.sim_timer.start()

    @pyqtSlot(object)
    def _on_db_response(self, response: ServiceResponse):
        if response.is_success:
            if response.operation == DbOperation.GET_ALL_OBJECTS:
                if isinstance(response.data, dict):
                    items_raw = response.data.get("items", [])
                    self.detection_templates = [
                        DetectionObject.from_dict(d) for d in items_raw
                    ]
                    print(
                        f"[SimServer] Loaded {len(self.detection_templates)} templates."
                    )

            elif response.operation in [
                DbOperation.ADD_OBJECT,
                DbOperation.UPDATE_OBJECT,
            ]:
                print("[SimServer] DB Changed. Refreshing templates...")
                self.db.request_all_objects()

    def _handle_new_connection(self):
        super()._handle_new_connection()
        print("[SimServer] Resetting session state for new client.")
        self.session_blacklist.clear()
        for target in self.active_targets:
            target.force_bg_send = True

        self.is_rf_streaming = False
        self.is_sound_streaming = False
        self._check_stream_timer()

    def _handle_hardware_command(self, action: str, data: Dict[str, Any]) -> None:
        """Перевизначення обробки команд заліза для симуляції."""
        if action == "get_gps":
            self._send_single_gps_response()

        elif action == "start_rf_stream":
            print("[SimServer] Starting RF Stream")
            self.is_rf_streaming = True
            self.is_sound_streaming = False
            self._check_stream_timer()

        elif action == "stop_rf_stream":
            self.is_rf_streaming = False
            self._check_stream_timer()

        elif action == "start_sound_stream":
            print("[SimServer] Starting Sound Stream")
            self.is_sound_streaming = True
            self.is_rf_streaming = False
            self._check_stream_timer()

        elif action == "stop_sound_stream":
            self.is_sound_streaming = False
            self._check_stream_timer()

        elif action == "false_alarm":
            event_id = data.get("event_id")
            if event_id:
                print(f"[SimServer] False Alarm on {event_id}. Blacklisting.")
                self.session_blacklist.add(event_id)
                self.active_targets = [
                    t for t in self.active_targets if t.id != event_id
                ]

        else:
            super()._handle_hardware_command(action, data)

    def _check_stream_timer(self):
        should_run = self.is_rf_streaming or self.is_sound_streaming
        if should_run and not self.stream_timer.isActive():
            self.stream_timer.start()
        elif not should_run and self.stream_timer.isActive():
            self.stream_timer.stop()

    def _on_sim_tick(self):
        if not self.detection_templates:
            return

        dt = UPDATE_INTERVAL_MS / 1000.0
        if len(self.active_targets) < MAX_SIMULTANEOUS_TARGETS:
            if random.random() < 0.1:
                template = random.choice(self.detection_templates)
                self.active_targets.append(SimulatedTarget(template))

        next_targets = []
        for target in self.active_targets:
            if target.id in self.session_blacklist:
                continue

            if target.update(dt):
                bg_packet = target.check_and_get_background()
                if bg_packet:
                    self.send_packet("detection_background", bg_packet)

                event_dict = target.get_event_data()
                if event_dict:
                    self.send_packet("detection", event_dict)

                next_targets.append(target)

        self.active_targets = next_targets

    def _on_stream_tick(self):
        if self.is_rf_streaming:
            data = self._generate_mock_rf_data()
            self.send_packet("rf_stream", data)
        elif self.is_sound_streaming:
            data = self._generate_mock_sound_data()
            self.send_packet("sound_stream", data)

    def _generate_mock_rf_data(self) -> Dict[str, Any]:
        fft_size = 512
        spectrum_db = -100 + np.random.normal(0, 3, fft_size)
        data_uint8 = (
            (spectrum_db + DB_OFFSET).clip(UINT8_MIN, UINT8_MAX).astype(np.uint8)
        )
        return {
            "data_magnitude": data_uint8.tolist(),
            "center_freq_hz": 915_000_000.0,
            "sample_rate_hz": 10_000_000.0,
            "timestamp": time.time(),
        }

    def _generate_mock_sound_data(self) -> Dict[str, Any]:
        fft_size = 512
        spectrum_db = -80 + np.random.normal(0, 5, fft_size)
        data_uint8 = (
            (spectrum_db + DB_OFFSET).clip(UINT8_MIN, UINT8_MAX).astype(np.uint8)
        )
        return {
            "data_magnitude": data_uint8.tolist(),
            "center_freq_hz": 0,
            "sample_rate_hz": 44100.0,
            "timestamp": time.time(),
        }

    def _send_single_gps_response(self):
        self.gps_lat += random.uniform(-0.0001, 0.0001)
        self.gps_lon += random.uniform(-0.0001, 0.0001)
        gps = GPSData(
            lat=self.gps_lat, lon=self.gps_lon, strength=random.randint(80, 100)
        )
        self.send_gps_data(gps)


if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
    service = AdvancedNetworkUtility(port=6000)
    service.start()
    print("=== ADVANCED SIMULATION SERVER (REFACTORED) RUNNING ===")
    sys.exit(app.exec())

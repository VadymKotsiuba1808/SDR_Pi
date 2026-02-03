import sys
import json
import math
import random
import uuid
import time
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List, Set

from PyQt6.QtCore import (
    QCoreApplication,
    QObject,
    pyqtSlot,
    QByteArray,
    QTimer,
)
from PyQt6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress

# --- MOCK IMPORTS (Адаптуйте під структуру проекту) ---
from app.core.constants import DB_OFFSET, UINT8_MIN, UINT8_MAX
from temp.database_service import DatabaseService
from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.models.gps_data import GPSData
from app.models.service_response import ServiceResponse, DbOperation

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
    Відповідає за свій рух, параметри сигналу та генерацію власного фону.
    """

    def __init__(self, template: DetectionObject):
        # Цей ID буде спільним для DetectionEvent та DetectionBackground цього об'єкта
        self.id = str(uuid.uuid4())

        self.template = template
        self.name = template.name
        self.object_class = template.object_class
        self.is_dangerous = template.is_dangerous

        # --- Частоти ---
        self.base_freq = self._parse_frequency(template.rf_params_hz)
        self.current_freq = self.base_freq

        # --- Позиція ---
        angle_deg = random.uniform(0, 360)
        dist_m = random.uniform(
            SIMULATION_RADIUS_METERS * 0.4, SIMULATION_RADIUS_METERS
        )

        self.x = dist_m * math.cos(math.radians(angle_deg))
        self.y = dist_m * math.sin(math.radians(angle_deg))

        # --- Швидкість ---
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

        # Вектор руху
        angle_to_center = (angle_deg + 180) % 360
        move_angle = angle_to_center + random.uniform(-60, 60)

        self.vx = self.speed * math.cos(math.radians(move_angle))
        self.vy = self.speed * math.sin(math.radians(move_angle))

        # --- Поведінка ---
        self.behavior = random.choice(["linear", "linear", "circle", "zigzag"])

        # --- Сигнал ---
        self.confidence = random.uniform(0.6, 1.0)
        self.is_hidden = False
        self.hidden_until = 0.0

        # --- ЛОГІКА ФОНУ ---
        # Час наступної відправки фону.
        # Ставимо поточний час, щоб відправити перший пакет одразу при створенні.
        # Але також додаємо флаг force_bg_send для ручного виклику при підключенні клієнта.
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
        """Оновлює фізику. Повертає False, якщо об'єкт вилетів за межі."""
        now = time.time()

        # Логіка "зникнення" сигналу (імітація перешкод)
        if self.is_hidden:
            if now > self.hidden_until:
                self.is_hidden = False
                self.confidence = random.uniform(0.5, 0.8)
        else:
            if random.random() < 0.008:
                self.is_hidden = True
                self.hidden_until = now + random.uniform(1.5, 4.0)

        # Рух
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

        # Дрейф частоти (імітація Доплера або нестабільності передавача)
        self.current_freq = self.base_freq + random.uniform(-150, 150)

        dist_sq = self.x**2 + self.y**2
        if dist_sq > (SIMULATION_RADIUS_METERS * 1.1) ** 2:
            return False

        return True

    def get_event_data(self) -> Optional[Dict[str, Any]]:
        """
        Створює DetectionEvent і повертає його словникове представлення.
        """
        if self.is_hidden:
            return None

        dist_m = math.sqrt(self.x**2 + self.y**2)
        angle_rad = math.atan2(self.y, self.x)
        angle_deg = (math.degrees(angle_rad) + 360) % 360
        det_type = "Sound" if self.current_freq < 20000 else "RF"

        # Формуємо словник вручну
        return {
            "id": self.id,  # Спільний ID для треку
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
        """
        Перевіряє, чи настав час відправити фон для цього об'єкта.
        Якщо так - повертає словник DetectionBackground з тим самим ID.
        """
        now = time.time()

        # Перевірка: чи минув інтервал АБО чи стоїть прапорець примусової відправки
        if self.force_bg_send or (now - self.last_bg_time > TARGET_BG_INTERVAL_SEC):
            self.last_bg_time = now
            self.force_bg_send = False

            # Генеруємо "фон" навколо частоти об'єкта (імітація спектру)
            fft_size = 512
            rows = 100  # Генеруємо 2D матрицю (Waterfall), щоб все було красиво

            # 1. Базовий шум (2D матриця)
            noise_level = -105.0
            noise = np.random.normal(0, 2.0, (rows, fft_size)) + noise_level

            # 2. Можна додати "слід" цілі на водоспаді
            # Наприклад, вертикальна смуга посередині (якщо центр = частота цілі)
            center_col = fft_size // 2
            # Симулюємо невелике "гуляння" частоти (дрейф)
            for r in range(rows):
                drift = int(np.sin(r * 0.1) * 3)
                c = center_col + drift
                if 0 <= c < fft_size:
                    # Додаємо сигнал (~20 dB над шумом)
                    noise[r, max(0, c - 2) : min(fft_size, c + 3)] += 20.0

            # Конвертація в uint8
            data_uint8 = (noise + DB_OFFSET).clip(UINT8_MIN, UINT8_MAX).astype(np.uint8)

            return {
                "id": self.id,  # <--- ВАЖЛИВО: ID збігається з об'єктом
                "timestamp": datetime.now().isoformat(),
                "spectral_data": {
                    "center_freq_hz": self.base_freq,  # Центр на частоті об'єкта
                    "sample_rate_hz": 20_000_000.0,  # 20 MHz огляд
                    "duration_sec": 5.0,  # Історія за 5 секунд (100 рядків по 50мс)
                    "data_magnitude": data_uint8.tolist(),  # Список списків (2D)
                },
            }
        return None


class AdvancedNetworkUtility(QObject):
    """
    Головний клас сервісу симуляції.
    """

    def __init__(self, port: int = 6000, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.port = port
        self.server: Optional[QTcpServer] = None
        self.client_socket: Optional[QTcpSocket] = None

        # --- DATABASE ---
        self.db = DatabaseService()
        self._setup_db_signals()

        # --- SIMULATION STATE ---
        self.active_targets: List[SimulatedTarget] = []
        self.detection_templates: List[DetectionObject] = []
        self.session_blacklist: Set[str] = set()

        # --- TIMERS ---
        # 1. Таймер симуляції (рух + генерація подій + генерація фону)
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._on_sim_tick)
        self.sim_timer.setInterval(UPDATE_INTERVAL_MS)

        # 2. Таймер потокових даних (швидкий - для графіків "Active View")
        self.stream_timer = QTimer(self)
        self.stream_timer.timeout.connect(self._on_stream_tick)
        self.stream_timer.setInterval(STREAM_INTERVAL_MS)

        # --- STREAM FLAGS ---
        self.is_rf_streaming = False
        self.is_sound_streaming = False

        # GPS Base coords (Shepetivka area approx)
        self.gps_lat = 50.18
        self.gps_lon = 27.06

    def start(self):
        """Ініціалізація та запуск."""
        print("[NetService] Initializing...")

        # 1. Завантаження шаблонів (через новий механізм)
        # request_all_objects тепер повертає ServiceResponse з data={"items": [...]}
        # Тому ми підписуємось на request_finished, а не на old signal
        self.db.request_all_objects()

        # 2. Запуск сервера
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._handle_new_connection)

        if self.server.listen(QHostAddress.SpecialAddress.Any, self.port):
            print(f"[NetService] Listening on port {self.port}")
            self.sim_timer.start()
        else:
            print(f"[NetService] Error starting server: {self.server.errorString()}")

    # --- DB SIGNAL CONNECTIONS ---
    def _setup_db_signals(self):
        # ЗАМІНЕНО: Підключаємось тільки до одного сигналу
        self.db.request_finished.connect(self._send_db_generic_response)

    @pyqtSlot(object)
    def _send_db_generic_response(self, response: ServiceResponse):
        """
        Універсальний обробник відповідей від БД.
        Відправляє результат клієнту і оновлює симуляцію, якщо треба.
        """
        # 1. Відправка клієнту
        packet_data = response.to_dict()
        self._send_packet("db_operation_result", packet_data)

        # 2. Оновлення симуляції (якщо це успішна зміна об'єктів або перше завантаження)
        if response.is_success:
            if response.operation == DbOperation.GET_ALL_OBJECTS:
                self._on_templates_loaded(response.data)

            elif response.operation in [
                DbOperation.ADD_OBJECT,
                DbOperation.UPDATE_OBJECT,
            ]:
                print(
                    "[NetService] DB Object changed. Refreshing simulation templates..."
                )
                self.db.request_all_objects()

    def _on_templates_loaded(self, data: Dict[str, Any]):
        """Callback для початкового завантаження шаблонів."""
        items_raw = data.get("items", [])
        if items_raw:
            self.detection_templates = [DetectionObject.from_dict(d) for d in items_raw]
            print(
                f"[NetService] Simulation loaded {len(self.detection_templates)} templates."
            )
        else:
            print("[NetService] WARNING: No objects in DB. Simulation will be empty.")

    # --- NETWORK HANDLING ---
    @pyqtSlot()
    def _handle_new_connection(self):
        if self.client_socket:
            print("[NetService] Dropping old connection.")
            self.client_socket.close()

        self.client_socket = self.server.nextPendingConnection()
        print(
            f"[NetService] Client connected: {self.client_socket.peerAddress().toString()}"
        )

        self.client_socket.readyRead.connect(self._read_socket_data)
        self.client_socket.disconnected.connect(self._on_client_disconnected)

        print("[NetService] New session started. Clearing False Alarm blacklist.")
        self.session_blacklist.clear()

        # === ВАЖЛИВО: ПРИ НОВОМУ ПІДКЛЮЧЕННІ ЗМУШУЄМО ВСІ ЦІЛІ ВІДПРАВИТИ ФОН ===
        print("[NetService] Resetting background timers for all active targets.")
        for target in self.active_targets:
            target.force_bg_send = True

        # Скидаємо стрімінг при новому підключенні
        self.is_rf_streaming = False
        self.is_sound_streaming = False
        self._check_stream_timer()

    @pyqtSlot()
    def _on_client_disconnected(self):
        print("[NetService] Client disconnected.")
        self.client_socket = None
        self.is_rf_streaming = False
        self.is_sound_streaming = False
        self._check_stream_timer()

    @pyqtSlot()
    def _read_socket_data(self):
        if not self.client_socket:
            return

        while self.client_socket.canReadLine():
            line = self.client_socket.readLine().trimmed()
            try:
                line_str = bytes(line).decode("utf-8")
                if not line_str:
                    continue

                packet = json.loads(line_str)
                action = packet.get("action")
                data = packet.get("data", {})

                self._process_command(action, data)

            except json.JSONDecodeError:
                print(f"[NetService] JSON Error: {line}")
            except Exception as e:
                print(f"[NetService] Process Error: {e}")

    def _process_command(self, action: str, data: Dict[str, Any]):
        print(f"[NetService] CMD: {action}")

        # --- GPS ON DEMAND ---
        if action == "get_gps":
            self._send_single_gps_response()
            return

        # --- FALSE ALARM LOGIC ---
        if action == "false_alarm":
            event_id = data.get("event_id")
            if event_id:
                print(
                    f"[NetService] !!! FALSE ALARM on ID {event_id}. Blacklisting for session."
                )
                self.session_blacklist.add(event_id)
                self.active_targets = [
                    t for t in self.active_targets if t.id != event_id
                ]
            return

        # --- STREAMING CONTROL ---
        if action == "start_rf_stream":
            print("[NetService] STARTING RF STREAM")
            self.is_rf_streaming = True
            self.is_sound_streaming = False  # Зазвичай лише один режим активний
            self._check_stream_timer()
            return

        if action == "stop_rf_stream":
            print("[NetService] STOPPING RF STREAM")
            self.is_rf_streaming = False
            self._check_stream_timer()
            return

        if action == "start_sound_stream":
            print("[NetService] STARTING SOUND STREAM")
            self.is_sound_streaming = True
            self.is_rf_streaming = False
            self._check_stream_timer()
            return

        if action == "stop_sound_stream":
            print("[NetService] STOPPING SOUND STREAM")
            self.is_sound_streaming = False
            self._check_stream_timer()
            return

        # --- HARDWARE CONTROL ---
        if action == "start_alarm":
            print(f"[NetService] HARDWARE: Relays ON")
            return
        if action == "stop_alarm":
            print(f"[NetService] HARDWARE: Relays OFF")
            return

        # --- DB PROXY COMMANDS (Updated for new Logic) ---

        # Обробляємо команди і викликаємо відповідні методи БД сервісу
        # DatabaseService тепер повертає результат через request_finished -> _send_db_generic_response

        if action == "db_request_page":
            self.db.request_objects_page(data.get("page", 1), data.get("size", 10))

        elif action == "db_request_add":
            obj_data = data.get("object")
            if obj_data:
                self.db.add_object(DetectionObject.from_dict(obj_data))

        elif action == "db_request_update":
            obj_data = data.get("object")
            if obj_data:
                self.db.update_object(DetectionObject.from_dict(obj_data))

        elif action == "db_request_delete":
            self.db.delete_object(data.get("id"))

        elif action == "db_request_classes":
            self.db.request_classes()

        elif action == "db_request_add_class":
            cls_data = data.get("class")
            if cls_data:
                self.db.add_class(ObjectClass.from_dict(cls_data))

        elif action == "db_request_rename_class":
            # Уніфікуємо логіку Update Class
            # Клієнт шле old_class/new_class, але для update_class нам треба об'єкт з ID
            old_cls_dict = data.get("old_class")
            new_cls_dict = data.get("new_class")

            if old_cls_dict and new_cls_dict:
                cls_id = old_cls_dict.get("id")
                new_name = new_cls_dict.get("name")
                if cls_id and new_name:
                    cls_obj = ObjectClass(id=cls_id, name=new_name)
                    self.db.update_class(cls_obj)

        elif action == "db_request_delete_class":
            self.db.delete_class(data.get("id"))

    def _check_stream_timer(self):
        """Вмикає або вимикає швидкий таймер залежно від потреби."""
        should_run = self.is_rf_streaming or self.is_sound_streaming
        if should_run and not self.stream_timer.isActive():
            self.stream_timer.start()
        elif not should_run and self.stream_timer.isActive():
            self.stream_timer.stop()

    # --- SIMULATION LOGIC ---
    def _on_sim_tick(self):
        """Один крок фізичної симуляції детекцій."""
        if not self.detection_templates:
            return

        dt = UPDATE_INTERVAL_MS / 1000.0

        # 1. Спавн
        if len(self.active_targets) < MAX_SIMULTANEOUS_TARGETS:
            spawn_chance = 0.05 + (
                0.1 * (1 - len(self.active_targets) / MAX_SIMULTANEOUS_TARGETS)
            )
            if random.random() < spawn_chance:
                template = random.choice(self.detection_templates)
                new_target = SimulatedTarget(template)
                self.active_targets.append(new_target)
                print(f"[Sim] Spawned: {new_target.name} (ID: {new_target.id})")

        # 2. Оновлення всіх цілей
        next_targets = []
        for target in self.active_targets:
            if target.id in self.session_blacklist:
                continue

            alive = target.update(dt)
            if alive:
                # А) Перевірка та відправка ФОНУ (якщо час прийшов)
                bg_packet = target.check_and_get_background()
                if bg_packet:
                    print(
                        f"[NetService] Sending BACKGROUND for {target.name} ({target.id})"
                    )
                    # ВАЖЛИВО: action має співпадати з обробником у PiNet (background_spectrum)
                    self._send_packet("detection_background", bg_packet)

                # Б) Відправка ДЕТЕКЦІЇ (кожен тік)
                event_dict = target.get_event_data()
                if event_dict:
                    self._send_packet("detection", event_dict)

                next_targets.append(target)
            else:
                print(f"[Sim] Despawned: {target.name}")

        self.active_targets = next_targets

    # --- STREAM GENERATION LOGIC (Для вкладки Stream) ---
    def _on_stream_tick(self):
        """Генерує та відправляє пакет потокових даних для графіків."""
        if self.is_rf_streaming:
            data = self._generate_mock_rf_data()
            self._send_packet("rf_stream", data)

        elif self.is_sound_streaming:
            data = self._generate_mock_sound_data()
            self._send_packet("sound_stream", data)

    def _generate_mock_rf_data(self) -> Dict[str, Any]:
        """Генерує фейковий спектр для RF (uint8)."""
        fft_size = 512

        # 1. Генерація базового шуму
        noise_level_db = -100
        noise_variation = np.random.normal(0, 3, fft_size)
        spectrum_db = noise_level_db + noise_variation

        # 2. Симуляція сигналу
        t = time.time()
        shift = np.sin(t * 1.5) * (fft_size * 0.3)
        x = np.arange(fft_size)
        center = fft_size // 2 + shift

        peak_height = 40
        peak_width = 10
        peak = np.exp(-((x - center) ** 2) / (2 * peak_width**2)) * peak_height

        spectrum_db += peak

        data_uint8 = (
            (spectrum_db + DB_OFFSET).clip(UINT8_MIN, UINT8_MAX).astype(np.uint8)
        )

        return {
            "data_magnitude": data_uint8.tolist(),
            "center_freq_hz": 915_000_000.0,
            "sample_rate_hz": 10_000_000.0,
            "timestamp": t,
        }

    def _generate_mock_sound_data(self) -> Dict[str, Any]:
        """Генерує фейковий спектр для звуку (uint8)."""
        fft_size = 512
        x = np.linspace(0, 100, fft_size)

        noise_db = -80 + np.random.normal(0, 2, fft_size)

        t = time.time()
        tone1_pos = 50 + np.sin(t * 5) * 5
        tone1 = np.exp(-((np.arange(fft_size) - tone1_pos) ** 2) / 10) * 50
        tone2_pos = 150 + np.sin(t * 5) * 5
        tone2 = np.exp(-((np.arange(fft_size) - tone2_pos) ** 2) / 10) * 30

        spectrum_db = noise_db + tone1 + tone2

        data_uint8 = (
            (spectrum_db + DB_OFFSET).clip(UINT8_MIN, UINT8_MAX).astype(np.uint8)
        )

        return {
            "data_magnitude": data_uint8.tolist(),
            "center_freq_hz": 0,
            "sample_rate_hz": 44100.0,
            "timestamp": t,
        }

    def _send_single_gps_response(self):
        self.gps_lat += random.uniform(-0.0000005, 0.0000005)
        self.gps_lon += random.uniform(-0.0000005, 0.0000005)
        strength = random.randint(70, 100)
        gps_data = GPSData(lat=self.gps_lat, lon=self.gps_lon, strength=strength)
        print("[NetService] Sending GPS Response.")
        self._send_packet("gps_position", gps_data.to_dict())

    # --- SENDER HELPERS ---
    def _send_packet(self, action: str, data: Any):
        if (
            not self.client_socket
            or self.client_socket.state() != QTcpSocket.SocketState.ConnectedState
        ):
            return

        payload = {
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            msg = json.dumps(payload) + "\n"
            self.client_socket.write(QByteArray(msg.encode("utf-8")))
            self.client_socket.flush()
        except Exception as e:
            print(f"[NetService] Send Error: {e}")


if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
    service = AdvancedNetworkUtility(port=6000)
    service.start()
    print("=== ADVANCED SIMULATION SERVER RUNNING ===")
    sys.exit(app.exec())

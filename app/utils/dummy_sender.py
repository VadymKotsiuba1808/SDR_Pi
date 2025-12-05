"""
Симулятор відправника даних (Smart Sender).
Protocol V2: {"action": "type", "data": { payload }}

Логіка:
- Підтримує список "активних" цілей.
- Оновлює їх положення (рухає) кожну секунду і відправляє оновлення.
- Додає нові цілі поступово за розкладом.
- Очищає екран дуже рідко (раз на 4 хвилини).
"""

import socket
import time
import json
import random
import uuid
from datetime import datetime

SERVER_IP = "192.168.1.76"
SERVER_PORT = 6000


# --- КЛАС СИМУЛЬОВАНОЇ ЦІЛІ ---
class SimTarget:
    def __init__(self, t_type, dist, angle, obj_class="drone"):
        self.id = str(uuid.uuid4())
        self.type = t_type
        self.dist = dist
        self.angle = angle
        self.object_class = obj_class
        self.confidence = random.uniform(0.8, 0.99)
        # Швидкість руху (зміна кута і дистанції за тик)
        self.d_angle = random.uniform(-2.0, 2.0)
        self.d_dist = random.uniform(-1.0, 1.0)

    def update(self):
        """Імітує рух об'єкта"""
        self.angle = (self.angle + self.d_angle) % 360
        self.dist += self.d_dist

        # Щоб не полетів в мінус або занадто далеко
        if self.dist < 10:
            self.d_dist = abs(self.d_dist)
        if self.dist > 1500:
            self.d_dist = -abs(self.d_dist)

    def get_payload(self):
        return {
            "id": self.id,
            "type": self.type,
            "object_class": self.object_class,
            "confidence": self.confidence,
            "timestamp": datetime.now().isoformat(),
            "distance": int(self.dist),
            "angle": self.angle,
        }


# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def get_gps_payload():
    base_lat = 49.43440
    base_lon = 27.00543
    return {
        "gps_lat": base_lat + random.uniform(-0.0005, 0.0005),
        "gps_lon": base_lon + random.uniform(-0.0005, 0.0005),
    }


def send_json(sock, action, data):
    packet = {"action": action, "data": data}
    try:
        sock.sendall((json.dumps(packet) + "\n").encode("utf-8"))
    except Exception as e:
        print(f"Send Error: {e}")


# --- ГОЛОВНИЙ ЦИКЛ ---
def run_sender():
    active_targets = []
    start_time = time.time()
    last_gps_update = 0
    cycle_duration = 240  # 4 хвилини цикл

    # Етапи сценарію (час у секундах від початку циклу -> дія)
    # Ми просто додаємо цілі, вони самі будуть жити і оновлюватися
    scenario_steps = [
        (5, "add", SimTarget("RF", 500, 45, "bird")),  # 5 сек: з'являється птах
        (20, "add", SimTarget("RF", 300, 180, "drone")),  # 20 сек: дрон
        (22, "add", SimTarget("RF", 320, 190, "drone")),  # 22 сек: ще дрон поруч
        (60, "add", SimTarget("Audio", 100, 270, "drone")),  # 1 хв: аудіо дрон близько
        (
            100,
            "add",
            SimTarget("RF", 1200, 90, "airplane"),
        ),  # 1:40: далекий літак (ободок)
        (150, "add", SimTarget("RF", 50, 0, "ufo")),  # 2:30: щось дуже близько
        (230, "clear", None),  # 3:50: ОЧИЩЕННЯ (тиша 10 сек)
    ]

    # Індекс виконаних кроків
    step_index = 0

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Connecting to {SERVER_IP}:{SERVER_PORT}...")
            sock.connect((SERVER_IP, SERVER_PORT))
            print("Connected! Starting Smart Simulation...")

            while True:
                current_time = time.time()
                elapsed = current_time - start_time

                # 1. Перевірка сценарію (додавання/видалення)
                if step_index < len(scenario_steps):
                    trigger_time, action, target = scenario_steps[step_index]

                    if elapsed >= trigger_time:
                        if action == "add":
                            active_targets.append(target)
                            print(
                                f"[SCENARIO] Added target: {target.object_class} ({target.type})"
                            )
                        elif action == "clear":
                            active_targets.clear()
                            print("[SCENARIO] CLEAR ALL TARGETS (Silence...)")

                        step_index += 1

                # 2. Перезапуск циклу через 4 хвилини
                if elapsed > cycle_duration:
                    print("[SYSTEM] Restarting 4-minute cycle...")
                    start_time = time.time()
                    step_index = 0
                    active_targets.clear()

                # 3. Оновлення та відправка АКТИВНИХ цілей (Heartbeat 1Hz)
                if active_targets:
                    print(f"--- Updating {len(active_targets)} targets ---")
                    for t in active_targets:
                        t.update()  # Рухаємо ціль
                        send_json(sock, "detection", t.get_payload())
                else:
                    # Keep alive якщо пусто
                    send_json(sock, "keep_alive", {})
                    print(".", end="", flush=True)

                # 4. GPS оновлення (раз на 5 сек)
                if current_time - last_gps_update > 5:
                    send_json(sock, "gps_position", get_gps_payload())
                    last_gps_update = current_time
                    print(" [GPS Updated]")

                # 5. Обробка вхідних команд (False Alarm)
                sock.setblocking(False)
                try:
                    raw = sock.recv(4096)
                    if raw:
                        req = json.loads(raw.decode("utf-8").strip())
                        if req.get("action") == "false_alarm":
                            e_id = req.get("data", {}).get("event_id")
                            print(f"!!! USER REPORTED FALSE ALARM: {e_id} !!!")
                            # Видаляємо ціль з активних, щоб вона зникла
                            active_targets = [t for t in active_targets if t.id != e_id]
                except (BlockingIOError, json.JSONDecodeError):
                    pass
                except ConnectionResetError:
                    break

                # Пауза 1 секунда (щоб дані оновлювались плавно, а не блимали)
                time.sleep(1.0)

        except Exception as e:
            print(f"Connection lost: {e}. Retry in 3 sec...")
            time.sleep(3)


if __name__ == "__main__":
    run_sender()

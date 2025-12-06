"""
Симулятор відправника даних (Smart Sender).
Protocol V2: {"action": "type", "data": { payload }}

Логіка:
- Автоматичне перепідключення при втраті звязку.
- GPS передає силу сигналу.
"""

import socket
import time
import json
import random
import uuid
from datetime import datetime

SERVER_IP = "192.168.1.76"
SERVER_PORT = 6000


class SimTarget:
    def __init__(self, t_type, dist, angle, obj_class="drone"):
        self.id = str(uuid.uuid4())
        self.type = t_type
        self.dist = dist
        self.angle = angle
        self.object_class = obj_class
        self.confidence = random.uniform(0.8, 0.99)
        # Швидкість руху
        self.d_angle = random.uniform(-2.0, 2.0)
        self.d_dist = random.uniform(-1.0, 1.0)

    def update(self):
        """Імітує рух об'єкта"""
        self.angle = (self.angle + self.d_angle) % 360
        self.dist += self.d_dist

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


def get_gps_payload():
    base_lat = 49.43440
    base_lon = 27.00543
    return {
        "gps_lat": base_lat,
        "gps_lon": base_lon,
        "gps_strength": random.randint(20, 100),
    }


def send_json(sock, action, data):
    """
    Відправляє дані. Не ловить помилки тут, щоб дозволити
    головному циклу обробити розрив з'єднання.
    """
    packet = {"action": action, "data": data}
    sock.sendall((json.dumps(packet) + "\n").encode("utf-8"))


def run_sender():
    active_targets = []
    start_time = time.time()
    last_gps_update = 0
    cycle_duration = 240

    scenario_steps = [
        (5, "add", SimTarget("Sound", 500, 45, "bird")),
        (20, "add", SimTarget("RF", 300, 180, "drone")),
        (22, "add", SimTarget("RF", 320, 190, "drone")),
        (60, "add", SimTarget("Sound", 100, 270, "drone")),
        (100, "add", SimTarget("RF", 1200, 90, "airplane")),
        (150, "add", SimTarget("RF", 50, 0, "ufo")),
        (230, "clear", None),
    ]

    step_index = 0

    # Зовнішній цикл для перепідключення
    while True:
        sock = None
        try:
            print(f"Connecting to {SERVER_IP}:{SERVER_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((SERVER_IP, SERVER_PORT))
            sock.settimeout(None)
            print("Connected! Starting simulation...")

            while True:
                current_time = time.time()
                elapsed = current_time - start_time

                if step_index < len(scenario_steps):
                    trigger_time, action, target = scenario_steps[step_index]
                    if elapsed >= trigger_time:
                        if action == "add":
                            active_targets.append(target)
                            print(f"[SCENARIO] Added: {target.object_class}")
                        elif action == "clear":
                            active_targets.clear()
                            print("[SCENARIO] CLEAR ALL")
                        step_index += 1

                if elapsed > cycle_duration:
                    print("[SYSTEM] Restarting cycle...")
                    start_time = time.time()
                    step_index = 0
                    active_targets.clear()

                if active_targets:
                    print(f"--- Updating {len(active_targets)} targets ---")
                    for t in active_targets:
                        t.update()
                        send_json(sock, "detection", t.get_payload())
                else:
                    send_json(sock, "keep_alive", {})
                    print(".", end="", flush=True)

                if current_time - last_gps_update > 5:
                    send_json(sock, "gps_position", get_gps_payload())
                    last_gps_update = current_time
                    print(" [GPS Sent]")

                sock.setblocking(False)
                try:
                    raw = sock.recv(4096)
                    if not raw:
                        raise ConnectionResetError("Server closed connection")

                    if raw:
                        req = json.loads(raw.decode("utf-8").strip())
                        if req.get("action") == "false_alarm":
                            e_id = req.get("data", {}).get("event_id")
                            print(f"!!! FALSE ALARM: {e_id} !!!")
                            active_targets = [t for t in active_targets if t.id != e_id]
                except (BlockingIOError, json.JSONDecodeError):
                    pass

                sock.setblocking(True)
                time.sleep(1.0)

        except (
            ConnectionRefusedError,
            ConnectionResetError,
            BrokenPipeError,
            socket.timeout,
        ) as e:
            print(f"\nConnection lost/failed: {e}. Retry in 3 sec...")
            time.sleep(3)
        except Exception as e:
            print(f"\nUnexpected Error: {e}. Retry in 3 sec...")
            time.sleep(3)
        finally:
            if sock:
                sock.close()


if __name__ == "__main__":
    run_sender()

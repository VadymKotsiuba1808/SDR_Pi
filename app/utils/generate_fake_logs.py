import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

LOGS_DIR: str = "logs"
FILENAME: str = f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
ENTRY_COUNT: int = 150

"""Набір утиліт для створення тестових логів"""


def _ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        print(f"[Generator] Creating directory: {path}")
        os.makedirs(path)


def _generate_detection_payload(obj_class: str) -> Dict[str, Any]:
    """Генерує payload для події типу Detection."""
    det_id = str(uuid.uuid4())
    det_type = random.choice(["RF", "Sound"])

    # Логіка частот
    freq = 0.0
    if det_type == "RF":
        freq = random.choice([433.9, 868.0, 915.0, 2400.0, 5800.0])
        # Додаємо трохи шуму до частоти
        freq += random.uniform(-5.0, 5.0)
    else:
        freq = random.choice([400, 800, 1200, 3000])

    return {
        "id": det_id,
        "name": f"Target-{random.randint(100, 999)}",
        "object_class": obj_class,
        "type": det_type,
        "frequency": round(freq * 1_000_000, 2),  # Hz
        "distance": random.randint(50, 5000),
        "angle": round(random.uniform(0, 360), 1),
        "confidence": round(random.uniform(0.6, 0.99), 2),
    }


def _generate_false_alarm_payload(
    active_detections: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Генерує payload для події типу False Alarm на основі існуючих детекцій."""
    if not active_detections:
        return None

    target = random.choice(active_detections)

    return {
        "detection_id": target["id"],
        "name": target["name"],
    }


def generate_data(count: int) -> List[Dict[str, Any]]:
    """Основна функція генерації логів."""
    print(f"[Generator] Starting generation of {count} entries...")

    data: List[Dict[str, Any]] = []
    start_time = datetime.now() - timedelta(hours=2)

    active_detections: List[Dict[str, Any]] = []
    classes = ["Mavic 3", "Autel Evo", "FPV Kamikaze", "Shahed-136", "Orlan-10"]

    for i in range(count):
        current_time = start_time + timedelta(seconds=i * random.randint(10, 60))
        timestamp_str = current_time.isoformat()

        # 90% це детекції, 10% це хибні тривоги
        is_detection = random.random() > 0.1

        entry: Dict[str, Any] = {}

        if is_detection:
            obj_class = random.choice(classes)
            payload = _generate_detection_payload(obj_class)

            payload["timestamp"] = timestamp_str

            entry = {
                "type": "detection",
                "timestamp": timestamp_str,
                "payload": payload,
            }

            active_detections.append(payload)
        else:
            payload = _generate_false_alarm_payload(active_detections)

            if not payload:
                continue

            entry = {
                "type": "false_alarm",
                "timestamp": timestamp_str,
                "payload": payload,
            }

        data.append(entry)

        if (i + 1) % 50 == 0:
            print(f"[Generator] Generated {i + 1}/{count} entries...")

    print(f"[Generator] Generation completed. Total entries: {len(data)}")
    return data


def save_to_file(data: List[Dict[str, Any]], directory: str, filename: str) -> None:
    """Зберігає дані у JSON файл."""
    _ensure_dir(directory)
    path = os.path.join(directory, filename)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[Generator] Successfully saved to: {path}")
    except IOError as e:
        print(f"[Generator] Error saving file: {e}")


if __name__ == "__main__":
    logs = generate_data(ENTRY_COUNT)
    save_to_file(logs, LOGS_DIR, FILENAME)

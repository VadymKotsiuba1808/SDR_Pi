import json
import os
import random
import uuid
from datetime import datetime, timedelta

# Налаштування
LOGS_DIR = "logs"
FILENAME = f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
ENTRY_COUNT = 150  # Кількість записів

if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


def generate_data():
    data = []
    start_time = datetime.now() - timedelta(hours=2)

    # Список активних "треків" (щоб хибні тривоги посилались на реальні ID)
    active_detections = []

    classes = ["Mavic 3", "Autel Evo", "FPV Kamikaze", "Shahed-136", "Orlan-10"]

    for i in range(ENTRY_COUNT):
        # Час йде вперед
        current_time = start_time + timedelta(seconds=i * random.randint(10, 60))
        timestamp_str = current_time.isoformat()

        # 90% це детекції, 10% це хибні тривоги
        if random.random() > 0.1:
            # --- DETECTION ---
            det_id = str(uuid.uuid4())
            det_type = random.choice(["RF", "Sound"])
            obj_class = random.choice(classes)

            # Логіка частот
            freq = 0.0
            if det_type == "RF":
                freq = random.choice([433.9, 868.0, 915.0, 2400.0, 5800.0])
                # Додаємо трохи шуму до частоти
                freq += random.uniform(-5.0, 5.0)
            else:
                freq = random.choice([400, 800, 1200, 3000])  # Sound harmonics

            payload = {
                "id": det_id,
                "name": f"Target-{random.randint(100, 999)}",
                "object_class": obj_class,
                "type": det_type,
                "frequency": round(freq * 1000000, 2),
                "distance": random.randint(50, 5000),
                "angle": round(random.uniform(0, 360), 1),
                "confidence": round(random.uniform(0.6, 0.99), 2),
                "timestamp": timestamp_str,  # Дублюємо час у payload для зручності, хоча є в обгортці
            }

            entry = {
                "type": "detection",
                "timestamp": timestamp_str,
                "payload": payload,
            }

            data.append(entry)
            active_detections.append(payload)  # Зберігаємо для можливої хибної тривоги

        else:
            # --- FALSE ALARM ---
            if not active_detections:
                continue

            # Вибираємо випадкову попередню детекцію
            target = random.choice(active_detections)

            payload = {
                "detection_id": target["id"],
                "name": target["name"],
            }

            entry = {
                "type": "false_alarm",
                "timestamp": timestamp_str,
                "payload": payload,
            }
            data.append(entry)

    return data


if __name__ == "__main__":
    logs = generate_data()
    path = os.path.join(LOGS_DIR, FILENAME)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    print(f"Згенеровано {len(logs)} записів у файл: {path}")

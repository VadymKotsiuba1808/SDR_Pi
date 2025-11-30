"""
Симулятор відправника даних (Dummy Sender).
Допоміжний скрипт для тестування мережевого коду. Генерує та відправляє тестові (фейкові) пакети даних, емулюючи роботу другого Raspberry Pi.
"""

import socket
import time
import json
import itertools

SERVER_IP = "127.0.0.1"
SERVER_PORT = 6000

# --- НАБІР ТЕСТОВИХ ДАНИХ ---
# Сценарій:
# 1. Спокій (3 секунди)
# 2. З'явився RF сигнал далеко (2 секунди)
# 3. Дрон близько: RF + Звук (3 секунди) - тривога!
# 4. Дрон віддаляється: тільки RF (2 секунди)
# 5. Спокій (2 секунди)
TEST_SCENARIO = [
    # --- 1. Спокій ---
    {
        "rf_alert": False,
        "sound_alert": False,
        "gps_level": 4,
        "coord": [49.43440, 27.00543],
    },
    {
        "rf_alert": False,
        "sound_alert": False,
        "gps_level": 4,
        "coord": [49.43440, 27.00543],
    },
    {
        "rf_alert": False,
        "sound_alert": False,
        "gps_level": 4,
        "coord": [49.43440, 27.00543],
    },
    # --- 2. RF сигнал (далеко) ---
    {
        "rf_alert": True,
        "sound_alert": False,
        "gps_level": 3,
        "coord": [49.43450, 27.00550],
    },
    {
        "rf_alert": True,
        "sound_alert": False,
        "gps_level": 3,
        "coord": [49.43460, 27.00560],
    },
    # --- 3. ПІК ТРИВОГИ (близько) ---
    {
        "rf_alert": True,
        "sound_alert": True,
        "gps_level": 2,
        "coord": [49.43470, 27.00570],
    },
    {
        "rf_alert": True,
        "sound_alert": True,
        "gps_level": 2,
        "coord": [49.43470, 27.00570],
    },
    {
        "rf_alert": True,
        "sound_alert": True,
        "gps_level": 2,
        "coord": [49.43470, 27.00570],
    },
    # --- 4. Віддаляється (тільки RF) ---
    {
        "rf_alert": True,
        "sound_alert": False,
        "gps_level": 3,
        "coord": [49.43460, 27.00560],
    },
    {
        "rf_alert": True,
        "sound_alert": False,
        "gps_level": 3,
        "coord": [49.43450, 27.00550],
    },
    # --- 5. Знову спокій ---
    {
        "rf_alert": False,
        "sound_alert": False,
        "gps_level": 4,
        "coord": [49.43440, 27.00543],
    },
    {
        "rf_alert": False,
        "sound_alert": False,
        "gps_level": 4,
        "coord": [49.43440, 27.00543],
    },
]


def run_sender():
    # Створюємо нескінченний ітератор по нашому сценарію
    data_cycle = itertools.cycle(TEST_SCENARIO)

    while True:
        try:
            print(f"Підключення до {SERVER_IP}:{SERVER_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_IP, SERVER_PORT))
            print("Підключено! Починаю відправку даних за сценарієм...")

            while True:
                # Беремо наступний набір даних з циклу
                data = next(data_cycle)

                # Додаємо мітку часу для реалістичності (опціонально)
                # data["timestamp"] = time.time()

                msg = json.dumps(data) + "\n"
                sock.sendall(msg.encode("utf-8"))
                print(f"Надіслано: RF={data['rf_alert']}, Sound={data['sound_alert']}")

                # --- Читання відповіді (без змін) ---
                sock.setblocking(False)
                try:
                    response = sock.recv(1024)
                    if response:
                        print(f"⚡ ОТРИМАНО КОНФІГ: {response.decode('utf-8').strip()}")
                        # Тут можна додати логіку обробки конфігу, якщо треба
                except BlockingIOError:
                    pass
                except ConnectionResetError:
                    print("З'єднання розірвано сервером.")
                    break
                finally:
                    sock.setblocking(True)

                time.sleep(1.5)  # Трохи повільніше, щоб встигати помічати зміни в GUI

        except Exception as e:
            print(f"Помилка з'єднання: {e}. Повтор через 3 сек...")
            time.sleep(3)


if __name__ == "__main__":
    run_sender()

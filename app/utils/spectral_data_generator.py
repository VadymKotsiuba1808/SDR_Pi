import numpy as np
import random
from app.models.detection_event import SpectralData


def generate_fake_spectral_data(rows: int = 128, cols: int = 256) -> SpectralData:
    """
    Генерує реалістичний набір спектральних даних для тестування.
    rows: Кількість часових відрізків (Waterfall height)
    cols: Кількість частотних бінів (Waterfall width)
    """
    # 1. Базовий термальний шум (0.1 - 0.2)
    data = np.random.normal(0.15, 0.05, (rows, cols))

    # 2. Постійні завади (наприклад, Wi-Fi або стаціонарні сигнали)
    # Створюємо "горби" на спектрі
    x = np.linspace(0, 1, cols)
    for _ in range(2):
        pos = random.uniform(0.7, 0.9)  # Зазвичай у верхній частині діапазону
        width = random.uniform(0.05, 0.1)
        peak = np.exp(-((x - pos) ** 2) / (2 * width**2)) * 0.2
        data += peak  # Додаємо до кожного рядка

    # 3. Сигнал об'єкта (FHSS - стрибаючі частоти)
    # Малюємо "цеглинки" сигналу
    current_row = 0
    while current_row < rows:
        duration = random.randint(5, 12)
        if random.random() > 0.3:  # 70% часу є сигнал
            freq_pos = random.randint(int(cols * 0.1), int(cols * 0.6))
            burst_width = random.randint(2, 5)

            end_row = min(current_row + duration, rows)
            end_col = min(freq_pos + burst_width, cols)

            # Робимо сигнал яскравим (0.7 - 1.0)
            data[current_row:end_row, freq_pos:end_col] += 0.6

        current_row += duration + random.randint(2, 5)

    # Обмежуємо значення та переводимо в uint8
    data = np.clip(data, 0, 1)
    data_uint8 = (data * 255).astype(np.uint8)

    return SpectralData(
        center_freq_hz=915_000_000.0,  # 915 MHz
        bandwidth_hz=10_000_000.0,  # 10 MHz
        duration_sec=2.0,
        data_uint8=data_uint8,
    )


# --- Приклад використання ---
# event = DetectionEvent.from_dict(...)
# event.spectral_data = generate_fake_spectral_data()

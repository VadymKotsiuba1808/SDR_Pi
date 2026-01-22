import numpy as np
import random
from app.models.detection_event import SpectralData

# Імпортуємо константи
from app.core.constants import UINT8_MIN, UINT8_MAX


def generate_fake_spectral_data(rows: int = 128, cols: int = 256) -> SpectralData:
    """
    Генерує реалістичний набір спектральних даних для тестування (Waterall).
    Дані генеруються в діапазоні 0.0-1.0, а потім масштабуються в uint8.
    """

    # 1. Базовий термальний шум (візуально ~15% від шкали)
    # Це дасть приблизно -90 dB при відображенні (якщо DB_OFFSET=127)
    data = np.random.normal(0.15, 0.05, (rows, cols))

    # 2. Постійні завади (наприклад, Wi-Fi або стаціонарні сигнали)
    x = np.linspace(0, 1, cols)
    for _ in range(2):
        pos = random.uniform(0.7, 0.9)  # Зазвичай у верхній частині діапазону
        width = random.uniform(0.05, 0.1)
        # Висота піку 0.2 (20% шкали)
        peak = np.exp(-((x - pos) ** 2) / (2 * width**2)) * 0.2
        data += peak

    # 3. Сигнал об'єкта (FHSS - стрибаючі частоти)
    current_row = 0
    while current_row < rows:
        duration = random.randint(5, 12)
        if random.random() > 0.3:  # 70% часу є сигнал
            freq_pos = random.randint(int(cols * 0.1), int(cols * 0.6))
            burst_width = random.randint(2, 5)

            end_row = min(current_row + duration, rows)
            end_col = min(freq_pos + burst_width, cols)

            # Робимо сигнал яскравим (+60% шкали)
            # Разом з шумом це буде ~0.75 (або ~190 у uint8 -> +63 dB)
            data[current_row:end_row, freq_pos:end_col] += 0.6

        current_row += duration + random.randint(2, 5)

    # 4. Нормалізація та конвертація в uint8
    # Обрізаємо все, що вилізло за межі 0.0-1.0
    data = np.clip(data, 0.0, 1.0)

    # Масштабуємо до 0-255, використовуючи константу
    data_uint8 = (data * UINT8_MAX).astype(np.uint8)

    return SpectralData(
        center_freq_hz=915_000_000.0,  # 915 MHz
        sample_rate_hz=10_000_000.0,  # 10 MHz
        duration_sec=2.0,
        data_magnitude=data_uint8,  # Передаємо готовий uint8
    )


# --- Приклад використання ---
# event = DetectionEvent.from_dict(...)
# event.spectral_data = generate_fake_spectral_data()

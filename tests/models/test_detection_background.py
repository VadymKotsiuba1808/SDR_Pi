"""
Модуль для тестування моделей фонового спектру.

Цей модуль містить юніт-тести для перевірки серіалізації та десеріалізації
класів `DetectionBackground` та `SpectralData`. Це критично для забезпечення
коректного обміну даними між сервером та клієнтом через JSON.
"""

import numpy as np

from app.models.detection_background import DetectionBackground, SpectralData


def test_spectral_data_serialization() -> None:
    """
    Тест серіалізації та десеріалізації SpectralData.

    Перевіряє, чи правильно конвертуються NumPy масиви у списки для JSON
    та чи зберігаються числові параметри після повного циклу перетворення.
    """
    # Створюємо тестову матрицю амплітуд (uint8 для економії місця)
    mag = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    data = {
        "center_freq_hz": 2400e6,
        "sample_rate_hz": 20e6,
        "duration_sec": 0.1,
        "data_magnitude": mag.tolist(),
    }

    # Створюємо об'єкт зі словника (імітація отримання JSON)
    obj = SpectralData.from_dict(data)

    # Перевіряємо цілісність даних
    assert obj.center_freq_hz == 2400e6, (
        "Центральна частота повинна відповідати вхідним даним"
    )
    assert np.array_equal(obj.data_magnitude, mag), (
        "Матриця амплітуд повинна бути ідентичною оригінальному масиву"
    )
    assert obj.to_dict() == data, (
        "Результуючий словник повинен збігатися з вхідними даними"
    )


def test_detection_background_serialization() -> None:
    """
    Тест серіалізації та десеріалізації DetectionBackground.

    Перевіряє вкладену серіалізацію (DetectionBackground -> SpectralData)
    та правильність обробки метаданих запису.
    """
    spec_data = {
        "center_freq_hz": 433e6,
        "sample_rate_hz": 2e6,
        "duration_sec": 1.0,
        "data_magnitude": [[10, 20]],
    }
    data = {
        "id": "bg-001",
        "timestamp": "2026-05-30T11:00:00",
        "spectral_data": spec_data,
    }

    # Десеріалізація всього об'єкта фону
    obj = DetectionBackground.from_dict(data)

    # Перевіряємо ідентифікатори та вкладені дані
    assert obj.id == "bg-001", "ID фонового запису має бути збережений"
    assert obj.spectral_data.center_freq_hz == 433e6, (
        "Вкладені спектральні дані повинні бути коректно ініціалізовані"
    )
    assert obj.to_dict() == data, (
        "Повний цикл серіалізації повинен повертати ідентичний словник"
    )

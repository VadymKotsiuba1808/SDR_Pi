from enum import StrEnum
from typing import List

"""
Модуль містить глобальні константи та статичні налаштування додатка.

Цей файл визначає параметри, які не передбачають прямої зміни користувачем,
включаючи налаштування безпеки, картографії, інтервали оновлення UI
та шляхи до системних файлів.
"""

# === SECURITY & ACCESS ===
# Хеш-сума ключа доступу для верифікації адміністратора.
# Використовується алгоритм SHA-256. Очікувана фраза: "my_super_secret_pi_key".
SECURITY_KEY_HASH: str = (
    "b7b12e8e9433d5f962a4424ab305f88f51fdaa7c69dc1f0aa6d94e2e9dd16ecd"
)
# Ім'я файлу-маркера, наявність якого на USB-накопичувачі ініціює скидання пароля.
SECURITY_KEY_FILENAME: str = ".sdr_reset.key"

# === MAPS & GEODATA ===
# Базовий URL для запитів до API MapTiler.
MAPS_API_URL: str = "https://api.maptiler.com/maps"
# Формат зображень тайлів мапи.
MAPS_IMG_FORMAT: str = "png"
# Коефіцієнт масштабування для Retina-дисплеїв.
MAPS_SCALE: str = "@2x"

# Мінімальна відстань переміщення (в метрах), необхідна для оновлення центру мапи.
# Запобігає зайвому дрибіжанню курсора через похибку GPS.
MIN_DISTANCE_THRESHOLD: float = 2.0
# Тривалість відсутності руху (в секундах), після якої об'єкт вважається нерухомим.
STATIONARY_SECONDS: int = 10

# === UI & TIMERS (ms) ===
# Інтервал оновлення годинника в інтерфейсі (1 секунда).
TIMER_INTERVAL_TIME_UPDATE: int = 1000
# Інтервал оновлення кадрів анімації радара для плавного відображення.
TIMER_INTERVAL_RADAR_ANIM: int = 60
# Інтервал перевірки статусу Wi-Fi з'єднання (30 секунд).
TIMER_INTERVAL_WIFI_UPDATE: int = 30000

# Перелік ідентифікаторів реле керування живленням.
RELAY_NAMES_LIST: List[str] = ["K1", "K2", "K3"]

# === DSP & VISUALIZATION ===
# Зсув для перетворення значень дБ у діапазон uint8 (0-255).
# Використовується для підготовки даних для Waterfall-діаграми.
DB_OFFSET: float = 255.0

# Стандартні межі для типу даних uint8.
UINT8_MIN: int = 0
UINT8_MAX: int = 255

# Межі візуального відображення спектру в децибелах.
VISUAL_MIN_DB: float = -130.0
VISUAL_MAX_DB: float = 0.0
# Розрахунковий динамічний діапазон візуалізації.
VISUAL_RANGE_DB: float = VISUAL_MAX_DB - VISUAL_MIN_DB

# Поріг шуму в форматі uint8 для відсікання фонових завад на Waterfall.
VISUAL_NOISE_FLOOR_UINT8: int = int(VISUAL_MIN_DB + DB_OFFSET)

# === SYSTEM & PATHS ===
# Періодичність сканування підключених USB-пристроїв.
USB_SCAN_INTERVAL_SECONDS: float = 1.5
# Розділювач, що використовується у рядках параметрів радіочастот.
RF_PARAMS__DIVIDER: str = "-"

# Шляхи до системних директорій для логів та медіафайлів.
LOGS_DIR_PATH: str = "./logs"
BACKGROUND_LOGS_DIR_PATH: str = "./logs/backgrounds"
MEDIA_DIR_PATH: str = "./media"


class CLEAN_TARGET_NAME(StrEnum):
    """
    Категорії даних, доступні для автоматичного або ручного очищення.

    Attributes:
        LOGS: Текстові файли журналів подій.
        SCREENSHOTS: Знімки екрана інтерфейсу.
        SCREEN_RECORDS: Відеозаписи захоплення екрана.
    """

    LOGS = "logs"
    SCREENSHOTS = "screenshots"
    SCREEN_RECORDS = "screen_records"


# === DEV & DEBUG ===
# Прапорець використання скомпільованих .py файлів замість динамічного завантаження .ui.
# Рекомендовано для Release-версій для прискорення запуску.
DEV_COMPILED_UI_USING_ENABLED: bool = True
# Візуальне відображення меж тайлів на мапі для налагодження кешування.
DEV_TILE_DIVIDER_ENABLED: bool = False

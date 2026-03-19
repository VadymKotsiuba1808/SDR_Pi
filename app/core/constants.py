from typing import List
from enum import Enum

"""
Файл зі статичними константами, які користувач не зможе напряму змінювати,
пізніше трішки перенесу сюди певні значення з config.ini
"""

# === SECURITY & ACCESS ===
# Хеш ключа доступу
# Згенеровано для фрази: "my_super_secret_pi_key"
SECURITY_KEY_HASH: str = (
    "b7b12e8e9433d5f962a4424ab305f88f51fdaa7c69dc1f0aa6d94e2e9dd16ecd"
)
# Файл-маркер скидання
SECURITY_KEY_FILENAME: str = ".sdr_reset.key"

# === MAPS & GEODATA ===
MAPS_API_URL: str = "https://api.maptiler.com/maps"
MAPS_IMG_FORMAT: str = "png"
MAPS_SCALE: str = "@2x"

# Поріг оновлення мапи (м)
MIN_DISTANCE_THRESHOLD: float = 2.0
# Час до статусу "нерухомий" (с)
STATIONARY_SECONDS: int = 10

# === UI & TIMERS (ms) ===
TIMER_INTERVAL_TIME_UPDATE: int = 1000
TIMER_INTERVAL_RADAR_ANIM: int = 60
TIMER_INTERVAL_WIFI_UPDATE: int = 30000

# Назви реле
RELAY_NAMES_LIST: List[str] = ["K1", "K2", "K3"]

# === DSP & VISUALIZATION ===
# Зсув для конвертації в uint8
DB_OFFSET: float = 255.0

UINT8_MIN: int = 0
UINT8_MAX: int = 255

# Межі відображення спектру (dB)
VISUAL_MIN_DB: float = -130.0
VISUAL_MAX_DB: float = 0.0
VISUAL_RANGE_DB: float = VISUAL_MAX_DB - VISUAL_MIN_DB

# Поріг шуму для waterfall (uint8)
VISUAL_NOISE_FLOOR_UINT8: int = int(VISUAL_MIN_DB + DB_OFFSET)

# === SYSTEM & PATHS ===
USB_SCAN_INTERVAL_SECONDS: float = 1.5
RF_PARAMS__DIVIDER: str = "-"

LOGS_DIR_PATH: str = "./logs"
BACKGROUND_LOGS_DIR_PATH: str = "./logs/backgrounds"
MEDIA_DIR_PATH: str = "./media"


class CLEAN_TARGET_NAME(Enum):
    """Категорії для очищення даних"""

    LOGS = "logs"
    SCREENSHOTS = "screenshots"
    SCREEN_RECORDS = "screen_records"


# === DEV & DEBUG ===
# Використання .ui -> .py файлів
DEV_COMPILED_UI_USING_ENABLED: bool = True
# Сітка тайлів мапи
DEV_TILE_DIVIDER_ENABLED: bool = False

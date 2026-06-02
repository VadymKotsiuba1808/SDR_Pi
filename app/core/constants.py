from enum import StrEnum
from typing import List

# SHA-256 хеш фрази "my_super_secret_pi_key"
SECURITY_KEY_HASH: str = (
    "b7b12e8e9433d5f962a4424ab305f88f51fdaa7c69dc1f0aa6d94e2e9dd16ecd"
)
SECURITY_KEY_FILENAME: str = ".sdr_reset.key"

MAPS_API_URL: str = "https://api.maptiler.com/maps"
MAPS_IMG_FORMAT: str = "png"
MAPS_SCALE: str = "@2x"

# Мінімальна відстань (м) для оновлення центру мапи
MIN_DISTANCE_THRESHOLD: float = 2.0
# Тривалість відсутності руху (с) для статусу нерухомості
STATIONARY_SECONDS: int = 10

TIMER_INTERVAL_TIME_UPDATE: int = 1000
TIMER_INTERVAL_RADAR_ANIM: int = 60
TIMER_INTERVAL_WIFI_UPDATE: int = 30000

RELAY_NAMES_LIST: List[str] = ["K1", "K2", "K3"]

# Зсув для перетворення дБ у діапазон uint8 (0-255)
DB_OFFSET: float = 255.0

UINT8_MIN: int = 0
UINT8_MAX: int = 255

VISUAL_MIN_DB: float = -130.0
VISUAL_MAX_DB: float = 0.0
VISUAL_RANGE_DB: float = VISUAL_MAX_DB - VISUAL_MIN_DB

# Поріг шуму в форматі uint8 для Waterfall
VISUAL_NOISE_FLOOR_UINT8: int = int(VISUAL_MIN_DB + DB_OFFSET)

USB_SCAN_INTERVAL_SECONDS: float = 1.5
RF_PARAMS__DIVIDER: str = "-"

LOGS_DIR_PATH: str = "./logs"
BACKGROUND_LOGS_DIR_PATH: str = "./logs/backgrounds"
MEDIA_DIR_PATH: str = "./media"


class CLEAN_TARGET_NAME(StrEnum):
    """
    Категорії даних для очищення.

    - `LOGS`: Журнали подій.
    - `SCREENSHOTS`: Знімки екрана.
    - `SCREEN_RECORDS`: Відеозаписи.
    """

    LOGS = "logs"
    SCREENSHOTS = "screenshots"
    SCREEN_RECORDS = "screen_records"


# Використання скомпільованих .py замість .ui (для Release)
DEV_COMPILED_UI_USING_ENABLED: bool = True
# Відображення меж тайлів мапи
DEV_TILE_DIVIDER_ENABLED: bool = False

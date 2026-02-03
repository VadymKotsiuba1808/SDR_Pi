from typing import List
from enum import Enum

"""
Файл зі статичними константами, які користувач не зможе напряму змінювати,
пізніше трішки перенесу сюди певні значення з config.ini
"""

# Згенеровано для фрази: "my_super_secret_pi_key"
SECURITY_KEY_HASH: str = (
    "b7b12e8e9433d5f962a4424ab305f88f51fdaa7c69dc1f0aa6d94e2e9dd16ecd"
)
SECURITY_KEY_FILENAME: str = ".sdr_reset.key"

USB_SCAN_INTERVAL_SECONDS: float = 1.5

RELAY_NAMES_LIST: List[str] = ["K1", "K2", "K3"]

MAPS_API_URL: str = "https://api.maptiler.com/maps"
MAPS_IMG_FORMAT: str = "png"
MAPS_SCALE: str = "@2x"

DEV_COMPILED_UI_USING_ENABLED: bool = True
DEV_TILE_DIVIDER_ENABLED: bool = False

RF_PARAMS__DIVIDER: str = "-"

LOGS_DIR_PATH: str = "./logs"
MEDIA_DIR_PATH: str = "./media"


class CLEAN_TARGET_NAME(Enum):
    LOGS = "logs"
    SCREENSHOTS = "screenshots"
    SCREEN_RECORDS = "screen_records"


# Константи системи

# Зміщення для конвертації uint8 <-> dB
DB_OFFSET = 255.0

UINT8_MIN = 0
UINT8_MAX = 255

# === ВІЗУАЛЬНІ МЕЖІ ГРАФІКІВ ===
VISUAL_MIN_DB = -130.0
VISUAL_MAX_DB = 0.0

# Розрахунок діапазону (130 dB)
VISUAL_RANGE_DB = VISUAL_MAX_DB - VISUAL_MIN_DB

# Розрахунок порогу для водоспаду (Visual Noise Floor)
# Все, що нижче -130 dB, буде вважатися "нулем" на графіку.
VISUAL_NOISE_FLOOR_UINT8 = int(VISUAL_MIN_DB + DB_OFFSET)

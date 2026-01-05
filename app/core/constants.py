from typing import List

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

"""
Файл зі статичними константами, які користувач не зможе напряму змінювати,
пізніше трішки перенесу сюди певні значення з config.ini
"""

from pathlib import Path

# Згенеровано для фрази: "my_super_secret_pi_key"
SECURITY_KEY_HASH = "b7b12e8e9433d5f962a4424ab305f88f51fdaa7c69dc1f0aa6d94e2e9dd16ecd"
SECURITY_KEY_FILENAME = ".sdr_reset.key"

USB_SCAN_INTERVAL_SECONDS = 1.5

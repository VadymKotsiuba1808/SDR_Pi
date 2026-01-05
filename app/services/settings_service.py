"""
Сервіс налаштувань.
Відповідає за валідацію, застосування змін на льоту та надання доступу до налаштувань для інших компонентів.
"""

import os
from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QFileSystemWatcher
from typing import NamedTuple, Any

from app.core.constants import RELAY_NAMES_LIST


class Setting(NamedTuple):
    section: str
    typ: type
    default: Any


class SettingsService(QObject):

    settings_changed = pyqtSignal()

    # Pinetwork
    pi_target_ip: str
    pi_target_port: int
    pi_is_receiver: bool
    # Maps
    radar_radius_km: float
    radar_max_radius_km: float
    api_key: str
    zoom: int
    # Auth
    role: str
    owner_password_hash: str
    remember_me: bool
    # Signal
    radio_range_ghz: list[float]
    # Timers
    gps_interval_s: int
    # Jammer
    main_relays: list[str]
    is_jammer_auto_start_enabled: bool
    is_jammer_auto_stop_enabled: bool
    jammer_auto_stop_interval_s: int
    # UI
    lang_code: str

    # Єдиний словник конфігурації: ключ → (секція, тип, значення за замовчуванням)
    _config_schema = {
        # Pinetwork
        "pi_target_ip": ("pinetwork", str, "0.0.0.0"),
        "pi_target_port": ("pinetwork", int, 6000),
        "pi_is_receiver": ("pinetwork", bool, True),
        # Maps
        "radar_radius_km": ("maps", float, 100),
        "radar_max_radius_km": ("maps", float, 200),
        "api_key": ("maps", str, ""),
        "zoom": ("maps", int, 15),
        # Auth
        "role": Setting("auth", str, "operator"),
        "owner_password_hash": Setting("auth", str, ""),
        "remember_me": Setting("auth", bool, False),
        # Signal
        "radio_range_ghz": ("signal", list, [0.0, 9.9]),
        # Timers
        "gps_interval_s": ("timers", int, 2),
        # Jammer
        "main_relays": ("jammer", list, [RELAY_NAMES_LIST[0]]),
        "is_jammer_auto_start_enabled": ("jammer", bool, False),
        "is_jammer_auto_stop_enabled": ("jammer", bool, False),
        "jammer_auto_stop_interval_s": ("jammer", int, 900),
        # UI
        "lang_code": ("ui", str, "uk"),
    }

    def __init__(self):
        super().__init__()
        file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../config.ini")
        )

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        self._settings = QSettings(file_path, QSettings.Format.IniFormat)

        # --- Завантаження початкових значень ---
        for key, (section, typ, default) in self._config_schema.items():
            value = self._settings.value(f"{section}/{key}", default, type=typ)
            super().__setattr__(key, value)  # уникаємо рекурсії

        # --- Відстеження змін у config.ini ---
        self._watcher = QFileSystemWatcher([self._settings.fileName()])
        self._watcher.fileChanged.connect(self._reload_from_file)

    def __setattr__(self, name, value):
        if name in self._config_schema:
            section, _, _ = self._config_schema[name]
            self._settings.setValue(f"{section}/{name}", value)
            super().__setattr__(name, value)
            self.settings_changed.emit()
        else:
            super().__setattr__(name, value)

    def _reload_from_file(self):
        """
        Перезавантажує дані, якщо config.ini змінено зовні.
        """
        print("Перезавантаження налаштувань з config.ini...")
        self._settings.sync()

        updated = False
        for key, (section, typ, default) in self._config_schema.items():
            new_value = self._settings.value(f"{section}/{key}", default, type=typ)
            if getattr(self, key) != new_value:
                super().__setattr__(key, new_value)
                updated = True

        if updated:
            self.settings_changed.emit()

    def sync(self):
        """Примусово записує зміни у файл."""
        self._settings.sync()

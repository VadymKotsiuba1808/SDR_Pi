"""
Сервіс налаштувань.
Відповідає за валідацію, застосування змін на льоту та надання доступу до налаштувань для інших компонентів.
"""

import os
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QFileSystemWatcher
from typing import NamedTuple, Any, Dict
from enum import Enum

from app.core.constants import RELAY_NAMES_LIST, CLEAN_TARGET_NAME
from app.models.settings import CleanRule


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
    radio_range_mhz: list[int]
    # Timers
    gps_interval_s: int
    # Jammer
    main_relays: list[str]
    is_jammer_auto_start_enabled: bool
    is_jammer_auto_stop_enabled: bool
    jammer_auto_stop_interval_s: int
    # Clean
    clean_settings: Dict[CLEAN_TARGET_NAME, CleanRule]
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
        "radio_range_mhz": ("signal", list, [100, 999]),
        # Timers
        "gps_interval_s": ("timers", int, 2),
        # Jammer
        "main_relays": ("jammer", list, [RELAY_NAMES_LIST[0]]),
        "is_jammer_auto_start_enabled": ("jammer", bool, False),
        "is_jammer_auto_stop_enabled": ("jammer", bool, False),
        "jammer_auto_stop_interval_s": ("jammer", int, 900),
        # Clean
        "clean_settings": ("clean", dict, {}),
        # UI
        "lang_code": ("ui", str, "uk"),
    }

    def __init__(self):
        super().__init__()

        config_path = Path(__file__).parents[2] / "config.ini"

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        self._settings = QSettings(str(config_path), QSettings.Format.IniFormat)

        self._load_all_settings()

        self._watcher = QFileSystemWatcher([self._settings.fileName()])
        self._watcher.fileChanged.connect(self._reload_from_file)

    def __setattr__(self, name: str, value: Any):
        """
        Перехоплює присвоєння атрибутів для автоматичного збереження в QSettings.
        """
        if name not in self._config_schema:
            return super().__setattr__(name, value)

        section, _, _ = self._config_schema[name]
        value_to_save = value

        # Спеціальна логіка для clean_settings
        if name == "clean_settings":
            value_to_save = self._serialize_clean_settings(value)

        # Зберігаємо в файл
        self._settings.setValue(f"{section}/{name}", value_to_save)

        super().__setattr__(name, value)
        self.settings_changed.emit()

    def _reload_from_file(self):
        """Перезавантажує дані, якщо файл змінено зовні."""
        print("[Settings] File changed externally, reloading...")
        self._settings.sync()

        if self._load_all_settings(check_if_changed=True):
            self.settings_changed.emit()

    def _load_all_settings(self, check_if_changed: bool = False) -> bool:
        """
        Універсальний метод завантаження всіх налаштувань.
        Повертає True, якщо хоча б одне налаштування змінилося.
        """
        updated = False

        for key, (section, typ, default) in self._config_schema.items():
            raw_value = self._settings.value(f"{section}/{key}", default, type=typ)

            # Обробка складних типів
            final_value = raw_value
            if key == "clean_settings" and isinstance(raw_value, dict):
                final_value = self._deserialize_clean_settings(raw_value)

            if check_if_changed:
                if getattr(self, key) != final_value:
                    super().__setattr__(key, final_value)
                    updated = True
            else:
                super().__setattr__(key, final_value)

        return updated

    def _serialize_clean_settings(
        self, value: Dict[CLEAN_TARGET_NAME, CleanRule]
    ) -> Dict[str, dict]:
        """Конвертує Dict[Enum, CleanRule] -> Dict[str, dict] для JSON/Ini."""
        if not isinstance(value, dict):
            return {}

        serialized = {}
        for target, rule in value.items():
            key_str = target.value if isinstance(target, Enum) else str(target)

            rule_dict = rule.to_dict() if hasattr(rule, "to_dict") else rule
            serialized[key_str] = rule_dict

        return serialized

    def _deserialize_clean_settings(
        self, value: Dict[str, dict]
    ) -> Dict[CLEAN_TARGET_NAME, CleanRule]:
        """Конвертує Dict[str, dict] -> Dict[Enum, CleanRule]."""
        parsed = {}
        for k, v in value.items():
            try:
                enum_key = CLEAN_TARGET_NAME(k)
                parsed[enum_key] = CleanRule.from_dict(v)
            except (ValueError, TypeError):
                continue
        return parsed

    def sync(self):
        """Примусово записує зміни у файл."""
        self._settings.sync()

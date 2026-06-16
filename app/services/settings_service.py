from enum import Enum
from pathlib import Path
from typing import Any, Dict, NamedTuple, Optional

from PyQt6.QtCore import QFileSystemWatcher, QObject, QSettings, pyqtSignal

from app.core.constants import CLEAN_TARGET_NAME, RELAY_NAMES_LIST
from app.core.logging_config import get_logger
from app.models.settings import CleanRule

logger = get_logger(__name__)


class Setting(NamedTuple):
    """Схема опису налаштування конфігурації."""

    section: str
    typ: type
    default: Any


class SettingsService(QObject):
    """Централізований сервіс керування налаштуваннями програми.

    Забезпечує збереження та завантаження параметрів з INI-файлу.

    !!! note
        Зміна будь-якого атрибута автоматично призводить до запису в INI-файл
        та випромінювання сигналу `settings_changed`.
    """

    settings_changed = pyqtSignal()

    # Pinetwork
    pi_target_ip: str
    pi_target_port: int

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

    # Detection
    detection_ttl_s: int

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

    _config_schema = {
        # Pinetwork
        "pi_target_ip": ("pinetwork", str, "10.0.0.1"),
        "pi_target_port": ("pinetwork", int, 6000),
        "radar_radius_km": ("maps", float, 100),
        "radar_max_radius_km": ("maps", float, 200),
        "api_key": ("maps", str, ""),
        "zoom": ("maps", int, 15),
        "role": Setting("auth", str, "operator"),
        "owner_password_hash": Setting("auth", str, ""),
        "remember_me": Setting("auth", bool, False),
        "radio_range_mhz": ("signal", list, [100, 999]),
        "detection_ttl_s": ("detection", int, 3),
        "gps_interval_s": ("timers", int, 2),
        "main_relays": ("jammer", list, [RELAY_NAMES_LIST[0]]),
        "is_jammer_auto_start_enabled": ("jammer", bool, False),
        "is_jammer_auto_stop_enabled": ("jammer", bool, False),
        "jammer_auto_stop_interval_s": ("jammer", int, 900),
        "clean_settings": ("clean", dict, {}),
        "lang_code": ("ui", str, "uk"),
    }

    def __init__(self, config_path: Optional[Path] = None) -> None:
        super().__init__()

        if config_path is None:
            config_path = Path(__file__).parents[2] / "config.ini"

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        self._settings = QSettings(str(config_path), QSettings.Format.IniFormat)

        self._load_all_settings()

        self._watcher = QFileSystemWatcher([self._settings.fileName()])
        self._watcher.fileChanged.connect(self._reload_from_file)

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in self._config_schema:
            return super().__setattr__(name, value)

        section, _, _ = self._config_schema[name]
        value_to_save = value

        if name == "clean_settings":
            value_to_save = self._serialize_clean_settings(value)

        self._settings.setValue(f"{section}/{name}", value_to_save)

        super().__setattr__(name, value)
        self.settings_changed.emit()

    def _reload_from_file(self) -> None:
        logger.info("External configuration change detected, reloading...")
        self._settings.sync()

        if self._load_all_settings(check_if_changed=True):
            self.settings_changed.emit()

    def _load_all_settings(self, check_if_changed: bool = False) -> bool:
        """Завантажує налаштування зі схеми конфігурації."""
        updated = False

        for key, (section, typ, default) in self._config_schema.items():
            raw_value = self._settings.value(f"{section}/{key}", default, type=typ)

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
        """Серіалізує правила очистки для збереження."""
        if not isinstance(value, dict):
            return {}

        serialized: Dict[str, dict] = {}
        for target, rule in value.items():
            key_str = target.value if isinstance(target, Enum) else str(target)
            serialized[key_str] = rule.to_dict()

        return serialized

    def _deserialize_clean_settings(
        self, value: Dict[str, dict]
    ) -> Dict[CLEAN_TARGET_NAME, CleanRule]:
        """Відновлює об'єкти CleanRule з дикту."""
        parsed = {}
        for k, v in value.items():
            try:
                enum_key = CLEAN_TARGET_NAME(k)
                parsed[enum_key] = CleanRule.from_dict(v)
            except (ValueError, TypeError):
                continue
        return parsed

    def sync(self) -> None:
        self._settings.sync()

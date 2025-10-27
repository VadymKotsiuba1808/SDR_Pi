import os
from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QFileSystemWatcher
from typing import NamedTuple, Any


class Setting(NamedTuple):
    section: str
    typ: type
    default: Any


class SettingsService(QObject):

    settings_changed = pyqtSignal()

    # Єдиний словник конфігурації: ключ → (секція, тип, значення за замовчуванням)
    _config_schema = {
        "host": ("network", str, "0.0.0.0"),
        "port": ("network", int, 5000),
        "radar_radius": ("maps", int, 500),
        "radar_max_radius": ("maps", int, 1000),
        "api_key": ("maps", str, ""),
        "base_url": ("maps", str, "https://api.maptiler.com/maps"),
        "scale": ("maps", str, "@2x"),
        "zoom": ("maps", int, 15),
        "img_format": Setting("maps", str, "png"),
        "role": Setting("auth", str, "operator"),
        "owner_password_hash": Setting("auth", str, ""),
        "remember_me": Setting("auth", bool, False),
        "tile_divider_enabled": Setting("dev", bool, False),
        "radio_range_GHz": ("signal", list, [0.0, 9.9]),
        "sound_range_GHz": ("signal", list, [0.0, 9.9]),
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

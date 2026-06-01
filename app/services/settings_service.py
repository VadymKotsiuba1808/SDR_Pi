from enum import Enum
from pathlib import Path
from typing import Any, Dict, NamedTuple, Optional

from PyQt6.QtCore import QFileSystemWatcher, QObject, QSettings, pyqtSignal

from app.core.constants import CLEAN_TARGET_NAME, RELAY_NAMES_LIST
from app.models.settings import CleanRule


class Setting(NamedTuple):
    """Структура опису окремого налаштування для схеми конфігурації.

    Attributes:
        section: Секція в INI-файлі, до якої належить налаштування.
        typ: Тип даних (int, float, str, bool, list, dict), використовується для приведення типів.
        default: Значення за замовчуванням, якщо налаштування відсутнє у файлі.
    """

    section: str
    typ: type
    default: Any


class SettingsService(QObject):
    """Централізований сервіс керування налаштуваннями програми.

    Забезпечує збереження та завантаження параметрів з INI-файлу, автоматичну
    синхронізацію при зміні атрибутів класу та відстеження зовнішніх змін файлу
    конфігурації.

    !!! note
        Сервіс реалізує реактивну модель: зміна будь-якого атрибута (наприклад,
        `service.zoom = 10`) автоматично призводить до запису в INI-файл та
        випромінювання сигналу `settings_changed`.

    Attributes:
        settings_changed: Сигнал, що випромінюється при будь-якій зміні налаштувань.
    """

    settings_changed = pyqtSignal()

    # Pinetwork
    pi_target_ip: str
    """IP-адреса сервера Raspberry Pi."""
    pi_target_port: int
    """Порт сервера Raspberry Pi."""

    # Maps
    radar_radius_km: float
    """Поточний радіус відображення на радарі (км)."""
    radar_max_radius_km: float
    """Максимально допустимий радіус радара (км)."""
    api_key: str
    """API ключ для доступу до тайлів мапи (Stadia Maps)."""
    zoom: int
    """Рівень масштабування мапи."""

    # Auth
    role: str
    """Поточна роль користувача (admin/operator)."""
    owner_password_hash: str
    """Хеш пароля адміністратора."""
    remember_me: bool
    """Чи зберігати сесію входу."""

    # Signal
    radio_range_mhz: list[int]
    """Діапазон радіочастот для сканування [min, max]."""

    # Detection
    detection_ttl_s: int
    """Час життя детекції без оновлення (секунди)."""

    # Timers
    gps_interval_s: int
    """Інтервал опитування GPS (секунди)."""

    # Jammer
    main_relays: list[str]
    """Список реле, що активуються кнопкою Jammer."""
    is_jammer_auto_start_enabled: bool
    """Чи активувати реле автоматично при детекції."""
    is_jammer_auto_stop_enabled: bool
    """Чи вимикати реле автоматично за таймером."""
    jammer_auto_stop_interval_s: int
    """Інтервал авто-стопу реле (секунди)."""

    # Clean
    clean_settings: Dict[CLEAN_TARGET_NAME, CleanRule]
    """Налаштування автоматичної очистки старих файлів."""

    # UI
    lang_code: str
    """Код мови інтерфейсу (uk/en)."""

    # Єдиний словник конфігурації: ключ → (секція, тип, значення за замовчуванням)
    _config_schema = {
        # Pinetwork
        "pi_target_ip": ("pinetwork", str, "10.0.0.1"),
        "pi_target_port": ("pinetwork", int, 6000),
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
        # Detection
        "detection_ttl_s": ("detection", int, 3),
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

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Ініціалізує сервіс та завантажує налаштування.

        Args:
            config_path: Шлях до INI-файлу. Якщо не вказано, використовується 'config.ini'
                у корені проекту.
        """
        super().__init__()

        if config_path is None:
            config_path = Path(__file__).parents[2] / "config.ini"

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        self._settings = QSettings(str(config_path), QSettings.Format.IniFormat)

        self._load_all_settings()

        # Використовуємо QFileSystemWatcher, щоб синхронізувати стан програми,
        # якщо користувач вручну редагує config.ini під час роботи.
        self._watcher = QFileSystemWatcher([self._settings.fileName()])
        self._watcher.fileChanged.connect(self._reload_from_file)

    def __setattr__(self, name: str, value: Any) -> None:
        """Перехоплює присвоєння атрибутів для синхронізації з файлом.

        Цей магічний метод дозволяє використовувати звичайний синтаксис Python для
        зміни налаштувань, автоматизуючи виклик QSettings.setValue.

        Args:
            name: Назва атрибута.
            value: Нове значення.
        """
        if name not in self._config_schema:
            return super().__setattr__(name, value)

        section, _, _ = self._config_schema[name]
        value_to_save = value

        # Налаштування очистки потребують серіалізації, оскільки містять складні об'єкти.
        if name == "clean_settings":
            value_to_save = self._serialize_clean_settings(value)

        # Зберігаємо в файл. QSettings автоматично обробляє базові типи.
        self._settings.setValue(f"{section}/{name}", value_to_save)

        super().__setattr__(name, value)
        self.settings_changed.emit()

    def _reload_from_file(self) -> None:
        """Перезавантажує дані при зовнішній зміні файлу.

        Синхронізує внутрішній стан QSettings з диском та оновлює атрибути
        сервісу, якщо вони фактично змінилися.
        """
        self._settings.sync()

        if self._load_all_settings(check_if_changed=True):
            self.settings_changed.emit()

    def _load_all_settings(self, check_if_changed: bool = False) -> bool:
        """Завантажує всі налаштування зі схеми конфігурації.

        Args:
            check_if_changed: Якщо True, метод лише порівнює значення і повертає
                ознаку наявності змін, не випромінюючи сигнали передчасно.

        Returns:
            True, якщо хоча б одне значення було змінено (при check_if_changed=True).
        """
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
        """Конвертує словник правил очистки у формат, придатний для збереження.

        Args:
            value: Словник з об'єктами CleanRule та ключами-Enums.

        Returns:
            Словник зі строковими ключами та примітивними типами даних.
        """
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
        """Відновлює об'єкти CleanRule зі збереженого словника.

        Args:
            value: Дані, прочитані з QSettings.

        Returns:
            Словник з типізованими ключами та об'єктами CleanRule.
        """
        parsed = {}
        for k, v in value.items():
            try:
                enum_key = CLEAN_TARGET_NAME(k)
                parsed[enum_key] = CleanRule.from_dict(v)
            except (ValueError, TypeError):
                continue
        return parsed

    def sync(self) -> None:
        """Примусово записує всі відкладені зміни у фізичний файл на диску."""
        self._settings.sync()

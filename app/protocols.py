"""
Протоколи (Typing Protocols).
Визначає абстрактні контракти для сервісів та компонентів переважно саме для налаштувань. Дозволяє використовувати Dependency Injection.
"""

from typing import Dict, Protocol

from app.core.constants import CLEAN_TARGET_NAME
from app.services.settings_service import CleanRule


class LangSettings(Protocol):
    lang_code: str


class MapServiceSettings(Protocol):
    api_key: str
    radar_max_radius_km: float
    zoom: int


class LoginDialogSettings(Protocol):
    role: str
    owner_password_hash: str
    remember_me: bool
    lang_code: str


class ChangePwdDialogSettings(Protocol):
    owner_password_hash: str
    lang_code: str


class SetMapDialogSettings(Protocol):
    radar_max_radius_km: float
    lang_code: str


class NetworkServiceSettings(Protocol):
    pi_target_ip: str
    pi_target_port: int
    pi_is_receiver: bool


class JammerServiceSettings(Protocol):
    main_relays: list[str]
    is_jammer_auto_stop_enabled: bool
    jammer_auto_stop_interval_s: int


class SettingsDialogSettings(Protocol):
    lang_code: str
    radar_max_radius_km: float
    gps_interval_s: int
    detection_ttl_s: int
    main_relays: list[str]
    is_jammer_auto_start_enabled: bool
    is_jammer_auto_stop_enabled: bool
    jammer_auto_stop_interval_s: int
    remember_me: bool
    clean_settings: Dict[CLEAN_TARGET_NAME, CleanRule]


class DetectionManagerSettings(Protocol):
    detection_ttl_s: int


class CleanerServiceSettings(Protocol):
    clean_settings: Dict[CLEAN_TARGET_NAME, CleanRule]


class OSService(Protocol):
    is_windows: bool
    is_linux: bool

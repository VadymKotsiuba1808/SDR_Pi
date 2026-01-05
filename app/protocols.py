"""
Протоколи (Typing Protocols).
Визначає абстрактні контракти для сервісів та компонентів переважно саме для налаштувань. Дозволяє використовувати Dependency Injection.
"""

from typing import Protocol


class LangSettings(Protocol):
    lang_code: str


class MapServiceSettings(Protocol):
    api_key: str
    radar_max_radius_km: int
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
    radar_max_radius_km: int
    lang_code: str


class SettingsDialogSettings(Protocol):
    lang_code: str
    radar_max_radius_km: float
    gps_interval_s: int
    main_relays: str
    is_jammer_auto_start_enabled: bool
    is_jammer_auto_stop_enabled: bool
    jammer_auto_stop_interval_s: int
    remember_me: bool


class OSService(Protocol):
    is_windows: bool
    is_linux: bool

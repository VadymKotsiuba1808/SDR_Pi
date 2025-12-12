"""
Протоколи (Typing Protocols).
Визначає абстрактні контракти для сервісів та компонентів переважно саме для налаштувань. Дозволяє використовувати Dependency Injection.
"""

from typing import Protocol


class MapServiceSettings(Protocol):
    api_key: str
    base_url: str
    radar_max_radius: int
    scale: float
    zoom: int
    img_format: str
    tile_divider_enabled: bool


class ApiServerSettings(Protocol):
    host: str
    port: int


class LoginDialogSettings(Protocol):
    role: str
    owner_password_hash: str
    remember_me: bool
    compiled_ui_using_enabled: bool
    lang_code: str


class ChangePwdDialogSettings(Protocol):
    owner_password_hash: str
    compiled_ui_using_enabled: bool
    lang_code: str


class SetMapDialogSettings(Protocol):
    radar_max_radius: int
    compiled_ui_using_enabled: bool
    lang_code: str


class RecordingStatusWidgetSettings(Protocol):
    compiled_ui_using_enabled: bool


class KeyboardWidgetSettings(Protocol):
    compiled_ui_using_enabled: bool
    lang_code: str


class ObjectEditorDialogSettings(Protocol):
    compiled_ui_using_enabled: bool
    lang_code: str


class ObjectManagerDialogSettings(Protocol):
    compiled_ui_using_enabled: bool
    lang_code: str


class OSService(Protocol):
    is_windows: bool
    is_linux: bool

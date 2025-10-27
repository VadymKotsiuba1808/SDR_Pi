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


class ChangePwdDialogSettings(Protocol):
    owner_password_hash: str

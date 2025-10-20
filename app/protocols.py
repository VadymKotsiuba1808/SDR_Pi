from typing import Protocol

class MapServiceSettings(Protocol):
    api_key:str
    base_url:str
    radar_max_radius:int
    scale:float

class ApiServerSettings(Protocol):
    host:str
    port:int
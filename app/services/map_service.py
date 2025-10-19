# -*- coding: utf-8 -*-
import requests
from enum import Enum
from PyQt6.QtGui import QPixmap
from settings_service import SettingsService

class MapTypes(Enum):
    """Перерахування для типів карт."""
    ROAD = "roadmap"
    SATELLITE = "satellite"
    TERRAIN = "terrain"
    HYBRID = "hybrid"

class MapService:
    """Клас для роботи з API карт. Ізолює всю логіку завантаження."""
  
    def __init__(self, settings: SettingsService):
        self.settings_service = settings

    def get_map_pixmap(self, coord: list, map_type: MapTypes, zoom: int = 16):
        """
        Завантажує карту і повертає її як об'єкт QPixmap.
        Повертає None у випадку помилки.
        """
        api_key= self.settings_service.api_key
        base_url=self.settings_service.base_url
        radar_max_radius=self.settings_service.radar_max_radius
        size=f"{radar_max_radius}x{radar_max_radius}"
        scale=self.settings_service.scale

        if not self.api_key:
            print("ПОМИЛКА: API ключ для Google Maps не вказано в config.ini")
            return None

        url = (
            f"{base_url}center={str(coord).replace('[', '').replace(']', '')}"
            f"&zoom={zoom}&size={size}&scale={scale}"
            f"&maptype={map_type.value}&key={api_key}"
        )
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Перевірка на HTTP помилки
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            return pixmap
            
        except requests.RequestException as e:
            print(f"Помилка завантаження карти: {e}")
            return None

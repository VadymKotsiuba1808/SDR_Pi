# -*- coding: utf-8 -*-
import requests
from enum import Enum
from PyQt5.QtGui import QPixmap

class MapTypes(Enum):
    """Перерахування для типів карт."""
    ROAD = "roadmap"
    SATELLITE = "satellite"
    TERRAIN = "terrain"
    HYBRID = "hybrid"

class MapService:
    """Клас для роботи з API карт. Ізолює всю логіку завантаження."""
    BASE_URL = "https://maps.googleapis.com/maps/api/staticmap?"
    SIZE = "901x901"  # Розмір радару
    SCALE = 2

    def __init__(self, api_key):
        self.api_key = api_key

    def get_map_pixmap(self, coord: list, map_type: MapTypes, zoom: int = 16):
        """
        Завантажує карту і повертає її як об'єкт QPixmap.
        Повертає None у випадку помилки.
        """
        if not self.api_key:
            print("ПОМИЛКА: API ключ для Google Maps не вказано в config.ini")
            return None

        url = (
            f"{self.BASE_URL}center={str(coord).replace('[', '').replace(']', '')}"
            f"&zoom={zoom}&size={self.SIZE}&scale={self.SCALE}"
            f"&maptype={map_type.value}&key={self.api_key}"
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

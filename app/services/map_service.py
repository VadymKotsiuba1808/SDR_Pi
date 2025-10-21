import httpx
from enum import Enum
from PyQt6.QtGui import QPixmap

from app.protocols import MapServiceSettings

class MapTypes(Enum):
    ROAD = "roadmap"
    SATELLITE = "satellite"
    TERRAIN = "terrain"
    HYBRID = "hybrid"

class MapService:
    """Асинхронний сервіс, що використовує httpx."""

    def __init__(self, settings: MapServiceSettings):
        self.settings_service = settings
        # Створюємо один клієнт для перевикористання
        self.client = httpx.AsyncClient()

    async def get_map_pixmap(self, coord: list, map_type: MapTypes, zoom: int = 16) -> QPixmap | None:
        """
        АСИНХРОННО завантажує карту і повертає QPixmap.
        У випадку помилки повертає None.
        """
        api_key = self.settings_service.api_key
        base_url = self.settings_service.base_url
        size = f"{self.settings_service.radar_max_radius}x{self.settings_service.radar_max_radius}"
        scale = self.settings_service.scale

        if not api_key:
            print("ПОМИЛКА: API ключ не вказано")
            return None

        url = (
            f"{base_url}center={str(coord).replace('[', '').replace(']', '')}"
            f"&zoom={zoom}&size={size}&scale={scale}"
            f"&maptype={map_type.value}&key={api_key}"
        )

        print(url)
        
        try:
            response = await self.client.get(url, timeout=10)
            response.raise_for_status()
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            return pixmap
            
        except httpx.RequestError as e:
            print(f"Помилка завантаження карти: {e}")
            return None
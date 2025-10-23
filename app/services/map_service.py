import math
import asyncio
from io import BytesIO
from enum import Enum
from PIL import Image, ImageDraw
import httpx
from PyQt6.QtGui import QPixmap

from app.protocols import MapServiceSettings


class MapTypes(Enum):
    ROAD = "streets-v2"
    SATELLITE = "satellite-v2"
    HYBRID = "hybrid"
    TERRAIN = "topo-v2"


class MapService:
    """Асинхронний сервіс, що завантажує карти з тайлів (MapTiler)."""

    TILE_SIZE = 512

    def __init__(self, settings: MapServiceSettings):
        self.settings_service = settings
        self.client = httpx.AsyncClient()

    def latlon_to_tile(self, lat: float, lon: float, zoom: int):
        """Конвертація координат у тайлові координати (x, y)."""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x_tile = (lon + 180.0) / 360.0 * n
        y_tile = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
        return x_tile, y_tile

    def tile_to_pixel_offset(self, lat: float, lon: float, zoom: int):
        """Повертає глобальний піксельний зсув (в пікселях)."""
        x_tile, y_tile = self.latlon_to_tile(lat, lon, zoom)
        return x_tile * self.TILE_SIZE, y_tile * self.TILE_SIZE

    async def download_tile(self, zoom: int, x: int, y: int, map_type: str, api_key: str) -> Image.Image:
        """Завантаження одного тайла."""
        url = f"https://api.maptiler.com/maps/{map_type}/{zoom}/{x}/{y}.png?key={api_key}"
        response = await self.client.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))

    async def get_map_pixmap(self, coord: list, map_type: MapTypes) -> QPixmap | None:
        """
        Асинхронно завантажує карту з тайлів навколо заданих координат.
        Повертає QPixmap або None у випадку помилки.
        """
        print(coord)
        lat, lon = coord
        api_key = self.settings_service.api_key
        zoom = self.settings_service.zoom
        size_px = int(self.settings_service.radar_max_radius)
        map_type_str = map_type.value

        if not api_key:
            print("ПОМИЛКА: API ключ не вказано")
            return None

        half_size = size_px // 2
        center_px_x, center_px_y = self.tile_to_pixel_offset(lat, lon, zoom)

        top_left_px_x = center_px_x - half_size
        top_left_px_y = center_px_y - half_size
        bottom_right_px_x = center_px_x + half_size
        bottom_right_px_y = center_px_y + half_size

        tile_x_min = int(top_left_px_x // self.TILE_SIZE)
        tile_y_min = int(top_left_px_y // self.TILE_SIZE)
        tile_x_max = int(bottom_right_px_x // self.TILE_SIZE)
        tile_y_max = int(bottom_right_px_y // self.TILE_SIZE)

        width = (tile_x_max - tile_x_min + 1) * self.TILE_SIZE
        height = (tile_y_max - tile_y_min + 1) * self.TILE_SIZE
        full_img = Image.new("RGB", (width, height))

        try:
            tasks = []
            positions = []

            for x in range(tile_x_min, tile_x_max + 1):
                for y in range(tile_y_min, tile_y_max + 1):
                    tasks.append(self.download_tile(zoom, x, y, map_type_str, api_key))
                    positions.append((x, y))

            tiles = await asyncio.gather(*tasks)

            for img, (x, y) in zip(tiles, positions):
                px = (x - tile_x_min) * self.TILE_SIZE
                py = (y - tile_y_min) * self.TILE_SIZE
                full_img.paste(img, (px, py))

                draw = ImageDraw.Draw(full_img)
                draw.rectangle([px, py, px + self.TILE_SIZE, py + self.TILE_SIZE], outline="red")

            offset_x = int(top_left_px_x - tile_x_min * self.TILE_SIZE)
            offset_y = int(top_left_px_y - tile_y_min * self.TILE_SIZE)
            cropped = full_img.crop((offset_x, offset_y, offset_x + size_px, offset_y + size_px))

            # Конвертуємо у QPixmap
            buffer = BytesIO()
            cropped.save(buffer, format="PNG")
            buffer.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            return pixmap

        except Exception as e:
            print(f"Помилка завантаження карти: {e}")
            return None

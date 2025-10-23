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

    async def download_tile(self,base_url:str, zoom: int, x: int, y: int, map_type: str,format:str, api_key: str) -> Image.Image:
        """Завантаження одного тайла."""
        url = f"{base_url}/{map_type}/{zoom}/{x}/{y}.{format.lower()}?key={api_key}"
        response = await self.client.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))

    async def get_map_pixmap(self, coord: list, map_type: MapTypes,coord_offset_px:list=[0,0], add_sizes_k:list=[1,1],) -> QPixmap | None:
        """
        Асинхронно завантажує карту з тайлів навколо заданих координат.
        Повертає QPixmap або None у випадку помилки.
        """
        base_url=self.settings_service.base_url
        lat, lon = coord
        api_key = self.settings_service.api_key
        zoom = self.settings_service.zoom
        add_width_k, add_height_k=add_sizes_k
        width_px = math.ceil(self.settings_service.radar_max_radius*add_width_k)
        height_px = math.ceil(self.settings_service.radar_max_radius*add_height_k)
        format=str(self.settings_service.img_format)
        map_type_str = map_type.value

        print("Width:", width_px)

        if not api_key:
            print("ПОМИЛКА: API ключ не вказано")
            return None

        half_width = width_px // 2
        half_height=height_px//2
        x_offset_px, y_offset_px=coord_offset_px
        center_px_x, center_px_y = self.tile_to_pixel_offset(lat, lon, zoom)
        center_px_x+=x_offset_px
        center_px_y+=y_offset_px

        top_left_px_x = center_px_x - half_width
        top_left_px_y = center_px_y - half_height
        bottom_right_px_x = center_px_x + half_width
        bottom_right_px_y = center_px_y + half_height

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
                    
                    tasks.append(self.download_tile(base_url=base_url, zoom=zoom, 
                    x=x, y=y, map_type=map_type_str,format=format, api_key=api_key))

                    positions.append((x, y))

            tiles = await asyncio.gather(*tasks)
            print("Count of tiles:",len(tasks))

            for img, (x, y) in zip(tiles, positions):
                px = (x - tile_x_min) * self.TILE_SIZE
                py = (y - tile_y_min) * self.TILE_SIZE
                full_img.paste(img, (px, py))

                draw = ImageDraw.Draw(full_img)
                draw.rectangle([px, py, px + self.TILE_SIZE, py + self.TILE_SIZE], outline="red")

            offset_x = int(top_left_px_x - tile_x_min * self.TILE_SIZE)
            offset_y = int(top_left_px_y - tile_y_min * self.TILE_SIZE)
            cropped = full_img.crop((offset_x, offset_y, offset_x + width_px, offset_y + height_px))

            # Конвертуємо у QPixmap
            buffer = BytesIO()
            cropped.save(buffer, format=format.upper())
            buffer.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            return pixmap

        except Exception as e:
            print(f"Помилка завантаження карти: {e}")
            return None

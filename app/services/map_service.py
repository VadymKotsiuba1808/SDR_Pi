import asyncio
import math
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageDraw
from PyQt6.QtGui import QPixmap

from app.core.constants import (
    DEV_TILE_DIVIDER_ENABLED,
    MAPS_API_URL,
    MAPS_IMG_FORMAT,
)
from app.protocols import MapServiceSettings


class MapTypes(Enum):
    ROAD = "streets-v2"
    # SATELLITE = "satellite-v2"
    HYBRID = "hybrid"
    TERRAIN = "topo-v2"


class MapService:
    """
    Сервіс мапи.
    Відповідає за роботу з геоданими, завантаження тайлів мапи, тощо.
    """

    TILE_SIZE: int = 512

    def __init__(self, settings: MapServiceSettings) -> None:
        self.settings_service: MapServiceSettings = settings
        self.client: httpx.AsyncClient = httpx.AsyncClient()

    def get_resolution_at_lat(self, zoom: int, lat: float) -> float:
        initial_res: float = 156543.03392
        res: float = (initial_res * math.cos(math.radians(lat))) / (2**zoom)
        return res * (256 / self.TILE_SIZE)

    def latlon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[float, float]:

        lat_rad: float = math.radians(lat)
        n: float = 2.0**zoom
        x_tile: float = (lon + 180.0) / 360.0 * n
        y_tile: float = (
            (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)
            / 2.0
            * n
        )
        return x_tile, y_tile

    def tile_to_pixel_offset(
        self, lat: float, lon: float, zoom: int
    ) -> Tuple[float, float]:

        x_tile, y_tile = self.latlon_to_tile(lat, lon, zoom)
        return x_tile * self.TILE_SIZE, y_tile * self.TILE_SIZE

    async def download_tile(
        self,
        base_url: str,
        zoom: int,
        x: int,
        y: int,
        map_type: str,
        format: str,
        api_key: str,
    ) -> Image.Image:

        url: str = (
            f"{base_url}/{map_type}/{zoom}/{x}/{y}.{format.lower()}?key={api_key}"
        )
        try:
            response = await self.client.get(url, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except Exception as e:
            print(f"[MapService] Error loading tile {x}/{y}: {e}")
            return Image.new("RGB", (self.TILE_SIZE, self.TILE_SIZE), (200, 200, 200))

    async def get_map_pixmap(
        self,
        coord: List[float],
        map_type: MapTypes,
        add_sizes_k: List[float] = [1, 1],
    ) -> Optional[Tuple[QPixmap, float]]:

        if not self.settings_service.api_key:
            print("[MapService] Error: API key missing.")
            return None

        lat, lon = coord

        geo_data = self._calculate_geometry(lat, lon, add_sizes_k)

        print(
            f"[MapService] Size: {geo_data['width_px']}x{geo_data['height_px']} | "
            f"Res: {geo_data['km_per_pixel']:.4f} km/px"
        )

        try:
            full_img = await self._fetch_and_stitch_tiles(geo_data, map_type)

            pixmap = self._crop_and_convert(full_img, geo_data)

            return (pixmap, geo_data["km_per_pixel"])

        except Exception as e:
            print(f"[MapService] Critical Map Error: {e}")
            return None

    def _calculate_geometry(
        self, lat: float, lon: float, add_sizes_k: List[float]
    ) -> Dict[str, Any]:

        zoom = self.settings_service.zoom
        radar_max_radius_km = self.settings_service.radar_max_radius_km
        add_width_k, add_height_k = add_sizes_k

        km_per_pixel = self.get_resolution_at_lat(zoom, lat) / 1000.0

        radius_px = radar_max_radius_km / km_per_pixel

        width_px = math.ceil(radius_px * 2 * add_width_k)
        height_px = math.ceil(radius_px * 2 * add_height_k)

        center_px_x, center_px_y = self.tile_to_pixel_offset(lat, lon, zoom)

        half_width = width_px // 2
        half_height = height_px // 2

        top_left_px_x = center_px_x - half_width
        top_left_px_y = center_px_y - half_height
        bottom_right_px_x = center_px_x + half_width
        bottom_right_px_y = center_px_y + half_height

        tile_x_min = int(top_left_px_x // self.TILE_SIZE)
        tile_y_min = int(top_left_px_y // self.TILE_SIZE)
        tile_x_max = int(bottom_right_px_x // self.TILE_SIZE)
        tile_y_max = int(bottom_right_px_y // self.TILE_SIZE)

        return {
            "km_per_pixel": km_per_pixel,
            "width_px": width_px,
            "height_px": height_px,
            "top_left_px_x": top_left_px_x,
            "top_left_px_y": top_left_px_y,
            "tile_x_min": tile_x_min,
            "tile_y_min": tile_y_min,
            "tile_x_max": tile_x_max,
            "tile_y_max": tile_y_max,
            "zoom": zoom,
        }

    async def _fetch_and_stitch_tiles(
        self, geo_data: Dict[str, Any], map_type: MapTypes
    ) -> Image.Image:

        base_url = MAPS_API_URL
        api_key = self.settings_service.api_key
        img_format = str(MAPS_IMG_FORMAT)
        map_type_str = map_type.value

        tile_x_min = geo_data["tile_x_min"]
        tile_x_max = geo_data["tile_x_max"]
        tile_y_min = geo_data["tile_y_min"]
        tile_y_max = geo_data["tile_y_max"]
        zoom = geo_data["zoom"]

        width_canvas = (tile_x_max - tile_x_min + 1) * self.TILE_SIZE
        height_canvas = (tile_y_max - tile_y_min + 1) * self.TILE_SIZE
        full_img = Image.new("RGB", (width_canvas, height_canvas))

        tasks = []
        positions: List[Tuple[int, int]] = []

        for x in range(tile_x_min, tile_x_max + 1):
            for y in range(tile_y_min, tile_y_max + 1):
                tasks.append(
                    self.download_tile(
                        base_url, zoom, x, y, map_type_str, img_format, api_key
                    )
                )
                positions.append((x, y))

        tiles = await asyncio.gather(*tasks)
        print(f"[MapService] Count of tiles: {len(tasks)}")

        for img, (x, y) in zip(tiles, positions):
            px = (x - tile_x_min) * self.TILE_SIZE
            py = (y - tile_y_min) * self.TILE_SIZE
            full_img.paste(img, (px, py))

            if DEV_TILE_DIVIDER_ENABLED:
                draw = ImageDraw.Draw(full_img)
                draw.rectangle(
                    [px, py, px + self.TILE_SIZE, py + self.TILE_SIZE],
                    outline="red",
                )

        return full_img

    def _crop_and_convert(
        self, full_img: Image.Image, geo_data: Dict[str, Any]
    ) -> QPixmap:

        img_format = str(MAPS_IMG_FORMAT)

        top_left_px_x = geo_data["top_left_px_x"]
        top_left_px_y = geo_data["top_left_px_y"]
        tile_x_min = geo_data["tile_x_min"]
        tile_y_min = geo_data["tile_y_min"]
        width_px = geo_data["width_px"]
        height_px = geo_data["height_px"]

        offset_x = int(top_left_px_x - tile_x_min * self.TILE_SIZE)
        offset_y = int(top_left_px_y - tile_y_min * self.TILE_SIZE)

        cropped = full_img.crop(
            (offset_x, offset_y, offset_x + width_px, offset_y + height_px)
        )

        buffer = BytesIO()
        cropped.save(buffer, format=img_format.upper())
        buffer.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.read())

        return pixmap

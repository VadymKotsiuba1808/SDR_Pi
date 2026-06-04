"""
Модуль для тестування сервісу мапи (MapService).
"""

import math
from unittest.mock import MagicMock

import pytest

from app.services.map_service import MapService


@pytest.fixture
def mock_map_settings() -> MagicMock:
    """Фікстура для макета налаштувань мапи."""
    settings = MagicMock()
    settings.api_key = "test_key"
    settings.zoom = 15
    settings.radar_max_radius_km = 1.0
    return settings


@pytest.fixture
def map_service(mock_map_settings: MagicMock) -> MapService:
    """Фікстура для ініціалізації MapService."""
    return MapService(mock_map_settings)


def test_get_resolution_at_lat(map_service: MapService) -> None:
    """Тест розрахунку роздільної здатності на різних широтах."""
    # Act
    res_eq = map_service.get_resolution_at_lat(15, 0)
    res_60 = map_service.get_resolution_at_lat(15, 60)

    # Assert
    assert math.isclose(res_60, res_eq * 0.5, rel_tol=1e-5), (
        "Resolution at 60 degrees latitude should be half of resolution at equator"
    )


def test_latlon_to_tile(map_service: MapService) -> None:
    """Тест перетворення координат у номери тайлів (Web Mercator)."""
    # Act & Assert
    x0, y0 = map_service.latlon_to_tile(0, 0, 0)
    assert x0 == 0.5, f"Expected x to be 0.5 for (0,0,0), got {x0}"
    assert y0 == 0.5, f"Expected y to be 0.5 for (0,0,0), got {y0}"

    x1, y1 = map_service.latlon_to_tile(0, 0, 1)
    assert x1 == 1.0, f"Expected x to be 1.0 for (0,0,1), got {x1}"
    assert y1 == 1.0, f"Expected y to be 1.0 for (0,0,1), got {y1}"


def test_calculate_geometry(map_service: MapService) -> None:
    """Тест розрахунку геометрії для склейки мапи."""
    # Arrange
    lat, lon = 50.45, 30.52
    km_per_px = map_service.get_resolution_at_lat(15, lat) / 1000.0
    expected_width = (1.0 / km_per_px) * 2

    # Act
    geo_data = map_service._calculate_geometry(lat, lon, add_sizes_k=[1, 1])

    # Assert
    assert "width_px" in geo_data, "geo_data must contain 'width_px'"
    assert "height_px" in geo_data, "geo_data must contain 'height_px'"
    assert "tile_x_min" in geo_data, "geo_data must contain 'tile_x_min'"
    assert geo_data["zoom"] == 15, f"Expected zoom 15, got {geo_data['zoom']}"

    assert math.isclose(geo_data["width_px"], expected_width, abs_tol=2), (
        f"Calculated width {geo_data['width_px']} differs from expected {expected_width}"
    )


@pytest.mark.anyio
async def test_download_tile_error_fallback(map_service: MapService) -> None:
    """Тест повернення заглушки при помилці завантаження тайла."""
    # Arrange
    map_service.client = MagicMock()
    map_service.client.get.side_effect = Exception("Network Error")

    # Act
    tile = await map_service.download_tile("url", 15, 1, 1, "type", "png", "key")

    # Assert
    assert tile.size == (512, 512), f"Expected tile size (512, 512), got {tile.size}"
    pixel_color = tile.getpixel((0, 0))
    assert pixel_color == (200, 200, 200), (
        f"Expected fallback color (200, 200, 200), got {pixel_color}"
    )

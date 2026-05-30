"""
Тести для сервісу мапи (MapService).
"""

import math
from unittest.mock import MagicMock

import pytest

from app.services.map_service import MapService


@pytest.fixture
def mock_map_settings():
    """Фікстура для макета налаштувань мапи."""
    settings = MagicMock()
    settings.api_key = "test_key"
    settings.zoom = 15
    settings.radar_max_radius_km = 1.0
    return settings


@pytest.fixture
def map_service(mock_map_settings):
    """Фікстура для ініціалізації MapService."""
    return MapService(mock_map_settings)


def test_get_resolution_at_lat(map_service):
    """Тест розрахунку роздільної здатності (м/піксель)."""
    # На екваторі (0°) роздільна здатність має бути максимальною
    res_eq = map_service.get_resolution_at_lat(15, 0)
    
    # На 60° паралелі cos(60) = 0.5, роздільна здатність має бути вдвічі меншою (більше пікселів на метр)
    res_60 = map_service.get_resolution_at_lat(15, 60)
    
    assert math.isclose(res_60, res_eq * 0.5, rel_tol=1e-5)


def test_latlon_to_tile(map_service):
    """Тест перетворення координат у номери тайлів (Web Mercator)."""
    # Нульові координати (центр мапи)
    x, y = map_service.latlon_to_tile(0, 0, 0)
    assert x == 0.5
    assert y == 0.5
    
    # Максимальний зум 1
    x, y = map_service.latlon_to_tile(0, 0, 1)
    assert x == 1.0
    assert y == 1.0


def test_calculate_geometry(map_service):
    """Тест розрахунку геометрії для склейки мапи."""
    lat, lon = 50.45, 30.52 # Київ
    
    geo_data = map_service._calculate_geometry(lat, lon, add_sizes_k=[1, 1])
    
    assert "width_px" in geo_data
    assert "height_px" in geo_data
    assert "tile_x_min" in geo_data
    assert geo_data["zoom"] == 15
    
    # Перевіримо, що ширина в пікселях відповідає заданому радіусу (1 км)
    km_per_px = map_service.get_resolution_at_lat(15, lat) / 1000.0
    expected_width = (1.0 / km_per_px) * 2
    
    # Має бути близьким до розрахованого
    assert math.isclose(geo_data["width_px"], expected_width, abs_tol=2)


@pytest.mark.anyio
async def test_download_tile_error_fallback(map_service):
    """Тест обробки помилки при завантаженні тайла (має повертати пусту картинку)."""
    # Емулюємо помилку в httpx (через мок клієнта)
    map_service.client = MagicMock()
    map_service.client.get.side_effect = Exception("Network Error")
    
    tile = await map_service.download_tile("url", 15, 1, 1, "type", "png", "key")
    
    assert tile.size == (512, 512)
    # Перевіримо колір пікселя (має бути світло-сірий за замовчуванням (200, 200, 200))
    assert tile.getpixel((0, 0)) == (200, 200, 200)

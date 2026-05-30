"""
Тести для логіки відображення мапи (MapViewLogic).
"""

import math

from PyQt6.QtCore import QPointF, QRect, QSize
from PyQt6.QtGui import QPixmap

from app.core.map_view_logic import MapViewLogic


def test_calculate_scale_factor():
    """Тест розрахунку коефіцієнта масштабування."""
    # Радіус 1км, ширина вікна 500пк (радіус 250пк) -> 250 пк/км
    # Роздільна здатність мапи 0.01 км/пк -> 100 пк/км
    # Scale = 250 / 100 = 2.5
    scale = MapViewLogic.calculate_scale_factor(
        radar_radius_km=1.0, radar_view_width_px=500, map_resolution_km_px=0.01
    )
    assert math.isclose(scale, 2.5), f"Scale factor calculation error: expected 2.5, got {scale}"


def test_calculate_scale_factor_zero():
    """Тест граничних значень для масштабування."""
    assert (
        MapViewLogic.calculate_scale_factor(0, 500, 0.01) == 0.0
    ), "Scale factor should be 0 when radar radius is 0"
    assert (
        MapViewLogic.calculate_scale_factor(1.0, 500, 0) == 0.0
    ), "Scale factor should be 0 when map resolution is 0"


def test_generate_view_pixmap_invalid_params(qtbot):
    """Тест генерації pixmap з невалідними параметрами."""
    pixmap = MapViewLogic.generate_view_pixmap(
        source_map=QPixmap(),
        view_size=QSize(100, 100),
        radar_center_relative=QPointF(0, 0),
        scale_factor=1.0,
    )
    assert pixmap.isNull(), "Generated pixmap should be null for empty source map"


def test_calculate_map_expansion_coefficients():
    """Тест розрахунку коефіцієнтів розширення мапи."""
    # Радар 200x200 (радіус 100), центр у (100, 100)
    # Фон 1000x1000
    # max_dist_x = max(100, 900) = 900
    # k_w = 900 / 100 = 9.0
    # k_w_final = 9.0 * 1.05 = 9.45
    radar_rect = QRect(0, 0, 200, 200)
    coeffs = MapViewLogic.calculate_map_expansion_coefficients(
        radar_rect=radar_rect, background_width=1000, background_height=1000
    )

    # k_w = 901 / 100 = 9.01
    # k_w_final = 9.01 * 1.05 = 9.4605
    assert math.isclose(
        coeffs[0], 9.4605
    ), f"Width expansion coefficient error: expected ~9.4605, got {coeffs[0]}"
    assert math.isclose(
        coeffs[1], 9.4605
    ), f"Height expansion coefficient error: expected ~9.4605, got {coeffs[1]}"


def test_calculate_map_expansion_zero():
    """Тест розрахунку коефіцієнтів при нульових розмірах."""
    assert MapViewLogic.calculate_map_expansion_coefficients(
        QRect(0, 0, 0, 0), 100, 100
    ) == [
        1.0,
        1.0,
    ], "Expansion coefficients should be 1.0 for empty radar rect"


"""Тести для логіки відображення мапи (MapViewLogic)."""

import math

from PyQt6.QtCore import QPointF, QRect, QSize
from PyQt6.QtGui import QPixmap

from app.core.map_view_logic import MapViewLogic


def test_calculate_scale_factor() -> None:
    # Розрахунок очікуваного: радіус 1 км, ширина 500 пк (радіус 250 пк) -> 250 пк/км.
    # Джерело: 0.01 км/пк -> 100 пк/км. Scale = 250 / 100 = 2.5.
    radar_radius_km = 1.0
    radar_view_width_px = 500
    map_resolution_km_px = 0.01

    scale = MapViewLogic.calculate_scale_factor(
        radar_radius_km=radar_radius_km,
        radar_view_width_px=radar_view_width_px,
        map_resolution_km_px=map_resolution_km_px,
    )

    assert math.isclose(scale, 2.5), (
        f"Scale factor calculation error: expected 2.5, got {scale}"
    )


def test_calculate_scale_factor_zero() -> None:
    # Функція повертає 0.0 при невалідних даних для запобігання діленню на нуль
    assert MapViewLogic.calculate_scale_factor(0, 500, 0.01) == 0.0, (
        "Scale factor should be 0 when radar radius is 0"
    )
    assert MapViewLogic.calculate_scale_factor(1.0, 500, 0) == 0.0, (
        "Scale factor should be 0 when map resolution is 0"
    )


def test_generate_view_pixmap_invalid_params(qtbot) -> None:
    pixmap = MapViewLogic.generate_view_pixmap(
        source_map=QPixmap(),
        view_size=QSize(100, 100),
        radar_center_relative=QPointF(0, 0),
        scale_factor=1.0,
    )
    assert pixmap.isNull(), "Generated pixmap should be null for empty source map"


def test_calculate_map_expansion_coefficients() -> None:
    # Радар 200x200 (радіус 100), центр (99, 99). Фон 1000x1000.
    # max_dist_x = 901. k_w = 9.01. З запасом 5%: 9.01 * 1.05 = 9.4605.
    radar_rect = QRect(0, 0, 200, 200)
    background_width = 1000
    background_height = 1000

    coeffs = MapViewLogic.calculate_map_expansion_coefficients(
        radar_rect=radar_rect,
        background_width=background_width,
        background_height=background_height,
    )

    assert math.isclose(coeffs[0], 9.4605), (
        f"Width expansion coefficient error: expected ~9.4605, got {coeffs[0]}"
    )
    assert math.isclose(coeffs[1], 9.4605), (
        f"Height expansion coefficient error: expected ~9.4605, got {coeffs[1]}"
    )


def test_calculate_map_expansion_zero() -> None:
    # Нейтральні коефіцієнти для порожнього прямокутника
    assert MapViewLogic.calculate_map_expansion_coefficients(
        QRect(0, 0, 0, 0), 100, 100
    ) == [
        1.0,
        1.0,
    ], "Expansion coefficients should be 1.0 for empty radar rect"

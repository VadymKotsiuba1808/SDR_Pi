"""
Тести для логіки відображення мапи (MapViewLogic).

Цей модуль містить набір тестів для перевірки математичних розрахунків,
пов'язаних із масштабуванням мапи, обрізанням зображення (viewport)
та обчисленням коефіцієнтів розширення для коректного рендерингу.
"""

import math

from PyQt6.QtCore import QPointF, QRect, QSize
from PyQt6.QtGui import QPixmap

from app.core.map_view_logic import MapViewLogic


def test_calculate_scale_factor() -> None:
    """Тест розрахунку коефіцієнта масштабування між мапою та екраном."""
    # Arrange: Задаємо параметри для розрахунку.
    # Радіус 1км, ширина вікна 500пк (радіус 250пк) -> цільова щільність 250 пк/км.
    # Роздільна здатність мапи 0.01 км/пк -> щільність джерела 100 пк/км.
    # Scale = 250 / 100 = 2.5.
    radar_radius_km = 1.0
    radar_view_width_px = 500
    map_resolution_km_px = 0.01

    # Act
    scale = MapViewLogic.calculate_scale_factor(
        radar_radius_km=radar_radius_km,
        radar_view_width_px=radar_view_width_px,
        map_resolution_km_px=map_resolution_km_px,
    )

    # Assert
    assert math.isclose(scale, 2.5), (
        f"Scale factor calculation error: expected 2.5, got {scale}"
    )


def test_calculate_scale_factor_zero() -> None:
    """Перевірка обробки некоректних або нульових вхідних даних для масштабування."""
    # !!! note: Функція повинна повертати 0.0, якщо радіус або роздільна здатність некоректні,
    # щоб уникнути ділення на нуль в інших частинах логіки.
    assert MapViewLogic.calculate_scale_factor(0, 500, 0.01) == 0.0, (
        "Scale factor should be 0 when radar radius is 0"
    )
    assert MapViewLogic.calculate_scale_factor(1.0, 500, 0) == 0.0, (
        "Scale factor should be 0 when map resolution is 0"
    )


def test_generate_view_pixmap_invalid_params(qtbot) -> None:
    """Перевірка того, що генерація pixmap повертає порожній об'єкт при невалідних параметрах."""
    pixmap = MapViewLogic.generate_view_pixmap(
        source_map=QPixmap(),
        view_size=QSize(100, 100),
        radar_center_relative=QPointF(0, 0),
        scale_factor=1.0,
    )
    assert pixmap.isNull(), "Generated pixmap should be null for empty source map"


def test_calculate_map_expansion_coefficients() -> None:
    """Тест розрахунку коефіцієнтів розширення мапи для повного заповнення фону."""
    # Arrange:
    # Радар 200x200 (радіус 100), центр у (99, 99) для QRect(0,0,200,200).
    # Фон 1000x1000.
    # max_dist_x = max(99, 1000-99) = 901.
    # k_w = 901 / 100 = 9.01.
    # Додаємо 5% запасу: k_w_final = 9.01 * 1.05 = 9.4605.
    radar_rect = QRect(0, 0, 200, 200)
    background_width = 1000
    background_height = 1000

    # Act
    coeffs = MapViewLogic.calculate_map_expansion_coefficients(
        radar_rect=radar_rect,
        background_width=background_width,
        background_height=background_height,
    )

    # Assert
    assert math.isclose(coeffs[0], 9.4605), (
        f"Width expansion coefficient error: expected ~9.4605, got {coeffs[0]}"
    )
    assert math.isclose(coeffs[1], 9.4605), (
        f"Height expansion coefficient error: expected ~9.4605, got {coeffs[1]}"
    )


def test_calculate_map_expansion_zero() -> None:
    """Перевірка розрахунку коефіцієнтів при нульових розмірах прямокутника радара."""
    # Якщо прямокутник порожній, коефіцієнти повинні бути нейтральними (1.0).
    assert MapViewLogic.calculate_map_expansion_coefficients(
        QRect(0, 0, 0, 0), 100, 100
    ) == [
        1.0,
        1.0,
    ], "Expansion coefficients should be 1.0 for empty radar rect"

"""
Модуль для тестування математичних утиліт графіків.
"""

from typing import Dict

import numpy as np
from PyQt6.QtGui import QColor, QImage

from app.utils.chart_math import ChartMath


def test_calculate_nice_axis_basic() -> None:
    """Перевіряє розрахунок "гарних" значень осі для стандартних вхідних даних."""
    nice_max, nice_step, actual_ticks = ChartMath.calculate_nice_axis(
        100, target_ticks=5
    )

    assert nice_max == 100, "Maximum value should be 100"
    assert nice_step == 20, "Step should be 20"
    assert actual_ticks == 5, "Number of ticks should be 5"


def test_calculate_nice_axis_small() -> None:
    """Перевіряє розрахунок значень осі для малих діапазонів (менше 1)."""
    nice_max, nice_step, actual_ticks = ChartMath.calculate_nice_axis(
        0.5, target_ticks=5
    )

    assert nice_max >= 0.5, "Maximum should be at least the input value"
    assert nice_step > 0, "Step should be positive"
    assert actual_ticks >= 1, "There should be at least one tick"


def test_calculate_nice_axis_zero() -> None:
    """Перевіряє поведінку алгоритму при нульовому вхідному значенні."""
    nice_max, nice_step, actual_ticks = ChartMath.calculate_nice_axis(0, target_ticks=5)
    assert nice_max == 10.0, "Default maximum 10 is expected for zero"


def test_get_color_for_id() -> None:
    """Перевіряє генерацію стабільних кольорів для ідентифікаторів об'єктів."""
    cache: Dict[str, QColor] = {}
    color1 = ChartMath.get_color_for_id("id1", cache)
    color2 = ChartMath.get_color_for_id("id2", cache)
    color1_again = ChartMath.get_color_for_id("id1", cache)

    assert isinstance(color1, QColor), "Result should be a QColor object"
    assert color1 != color2, "Colors for different IDs should differ"
    assert color1 == color1_again, "Color for the same ID should be stable"
    assert len(cache) == 2, "Cache should contain two unique colors"


def test_create_heatmap(qtbot) -> None:
    """Перевіряє перетворення 2D-масиву NumPy у зображення QImage."""
    data = np.zeros((10, 10), dtype=np.uint8)
    data[0, 0] = 255

    img = ChartMath.create_heatmap(data)

    assert isinstance(img, QImage), "Result should be a QImage object"
    assert img.width() == 10, "Image width should match the array width"
    assert img.height() == 10, "Image height should match the array height"
    assert img.format() == QImage.Format.Format_Indexed8, (
        "Indexed8 format should be used"
    )


def test_get_color_table(qtbot) -> None:
    """Перевіряє генерацію таблиці кольорів (Look-Up Table)."""
    table = ChartMath._get_color_table()

    assert isinstance(table, list), "Result should be a list"
    assert len(table) == 256, "Table should contain 256 colors"
    assert isinstance(table[0], int), "Table elements should be integers (ARGB)"

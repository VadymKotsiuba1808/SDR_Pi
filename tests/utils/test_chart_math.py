"""
Тести для математичних утиліт графіків (ChartMath).
"""

import numpy as np
from PyQt6.QtGui import QColor, QImage

from app.utils.chart_math import ChartMath


def test_calculate_nice_axis_basic():
    """Тест розрахунку кроків осі для стандартних значень."""
    nice_max, nice_step, actual_ticks = ChartMath.calculate_nice_axis(100, target_ticks=5)
    
    assert nice_max == 100
    assert nice_step == 20
    assert actual_ticks == 5


def test_calculate_nice_axis_small():
    """Тест розрахунку кроків осі для малих значень."""
    nice_max, nice_step, actual_ticks = ChartMath.calculate_nice_axis(0.5, target_ticks=5)
    
    assert nice_max >= 0.5
    assert nice_step > 0
    assert actual_ticks >= 1


def test_calculate_nice_axis_zero():
    """Тест розрахунку кроків осі для нуля."""
    nice_max, nice_step, actual_ticks = ChartMath.calculate_nice_axis(0, target_ticks=5)
    assert nice_max == 10.0


def test_get_color_for_id():
    """Тест генерації стабільних кольорів для ID."""
    cache = {}
    color1 = ChartMath.get_color_for_id("id1", cache)
    color2 = ChartMath.get_color_for_id("id2", cache)
    color1_again = ChartMath.get_color_for_id("id1", cache)
    
    assert isinstance(color1, QColor)
    assert color1 != color2
    assert color1 == color1_again
    assert len(cache) == 2


def test_create_heatmap(qtbot):
    """Тест створення QImage з numpy масиву."""
    data = np.zeros((10, 10), dtype=np.uint8)
    data[0, 0] = 255
    
    img = ChartMath.create_heatmap(data)
    
    assert isinstance(img, QImage)
    assert img.width() == 10
    assert img.height() == 10
    assert img.format() == QImage.Format.Format_Indexed8


def test_get_color_table(qtbot):
    """Тест генерації таблиці кольорів."""
    table = ChartMath._get_color_table()
    
    assert isinstance(table, list)
    assert len(table) == 256
    # Кожен елемент - це ARGB int
    assert isinstance(table[0], int)

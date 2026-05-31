"""
Тести для моделі CustomMapSettings (map_settings.py).
"""

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap

from app.models.map_settings import CustomMapSettings


def test_custom_map_settings_initialization(qtbot):
    """Тест ініціалізації CustomMapSettings."""
    pixmap = QPixmap(10, 10)
    center = QPoint(5, 5)
    settings = CustomMapSettings(
        pixmap=pixmap,
        px_per_km=100.0,
        rotation=45.0,
        total_diameter_km=2.0,
        center_px_point=center,
    )

    assert settings.pixmap == pixmap
    assert settings.px_per_km == 100.0
    assert settings.rotation == 45.0
    assert settings.center_px_point == center

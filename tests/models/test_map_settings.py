"""Тести для моделі CustomMapSettings."""

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap

from app.models.map_settings import CustomMapSettings


def test_custom_map_settings_initialization(qtbot) -> None:
    pixmap = QPixmap(10, 10)
    center = QPoint(5, 5)
    px_per_km = 100.0
    rotation = 45.0
    total_diameter_km = 2.0

    settings = CustomMapSettings(
        pixmap=pixmap,
        px_per_km=px_per_km,
        rotation=rotation,
        total_diameter_km=total_diameter_km,
        center_px_point=center,
    )

    assert settings.pixmap == pixmap, "Pixmap should be correctly stored"
    assert settings.px_per_km == px_per_km, "Pixels per km should be correctly stored"
    assert settings.rotation == rotation, "Rotation should be correctly stored"
    assert settings.center_px_point == center, "Center point should be correctly stored"
    assert settings.total_diameter_km == total_diameter_km, (
        "Total diameter should be correctly stored"
    )

"""
Модуль для тестування моделі налаштувань мапи.

Цей модуль містить юніт-тести для перевірки коректності ініціалізації
та поведінки класу CustomMapSettings.
"""

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap

from app.models.map_settings import CustomMapSettings


def test_custom_map_settings_initialization(qtbot) -> None:
    """
    Перевіряє коректність ініціалізації об'єкта CustomMapSettings.

    Тест ініціалізує об'єкт з набором параметрів та перевіряє, чи
    відповідають збережені значення вхідним даним.

    Args:
        qtbot: Фікстура pytest-qt для взаємодії з об'єктами Qt.
    """
    # Підготовка (Arrange)
    pixmap = QPixmap(10, 10)
    center = QPoint(5, 5)
    px_per_km = 100.0
    rotation = 45.0
    total_diameter_km = 2.0

    # Дія (Act)
    settings = CustomMapSettings(
        pixmap=pixmap,
        px_per_km=px_per_km,
        rotation=rotation,
        total_diameter_km=total_diameter_km,
        center_px_point=center,
    )

    # Перевірка (Assert)
    assert settings.pixmap == pixmap, "Pixmap should be correctly stored"
    assert settings.px_per_km == px_per_km, "Pixels per km should be correctly stored"
    assert settings.rotation == rotation, "Rotation should be correctly stored"
    assert settings.center_px_point == center, "Center point should be correctly stored"
    assert settings.total_diameter_km == total_diameter_km, (
        "Total diameter should be correctly stored"
    )

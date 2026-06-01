from dataclasses import dataclass

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap


@dataclass
class CustomMapSettings:
    """
    Клас для зберігання налаштувань користувацької карти та параметрів її масштабування.

    Attributes:
        pixmap (QPixmap): Графічне зображення карти (підкладка).
        px_per_km (float): Коефіцієнт масштабування (кількість пікселів на один кілометр).
        rotation (float): Кут повороту карти відносно півночі у градусах.
        total_diameter_km (float): Загальний робочий діаметр карти в кілометрах.
        center_px_point (QPoint): Координати центру карти в пікселях на зображенні.
    """

    pixmap: QPixmap
    px_per_km: float
    rotation: float
    total_diameter_km: float
    center_px_point: QPoint

from dataclasses import dataclass

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap


@dataclass
class CustomMapSettings:
    """Налаштування користувацької карти та параметри її масштабування.

    Attributes:
        pixmap: Графічне зображення карти (підкладка).
        px_per_km: Коефіцієнт масштабування (пікселів/км).
        rotation: Кут повороту відносно півночі (градуси).
        total_diameter_km: Робочий діаметр карти (км).
        center_px_point: Центр карти в пікселях.
    """

    pixmap: QPixmap
    px_per_km: float
    rotation: float
    total_diameter_km: float
    center_px_point: QPoint

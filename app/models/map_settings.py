from dataclasses import dataclass

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap


@dataclass
class CustomMapSettings:
    pixmap: QPixmap
    px_per_km: float
    rotation: float
    total_diameter_km: float
    center_px_point: QPoint

import math
from typing import Dict, Any, Optional

from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPixmap, QConicalGradient
from PyQt6.QtCore import Qt, QPointF

RADAR_POINT_SIZE = 20
RADAR_TEXT_OFFSET_Y_DEFAULT = -15
RADAR_TEXT_OFFSET_CORRECTION = 15
RADAR_BORDER_OFFSET = 15
RADAR_ANGLE_ROTATION_OFFSET = 90
RADAR_TEXT_ANGLE_THRESHOLD_LOW = 40
RADAR_TEXT_ANGLE_THRESHOLD_HIGH = 320


class RadarRenderer:
    """
    Клас відповідає виключно за малювання (Rendering) елементів радара.
    """

    def __init__(self):
        self.radar_angle = 0

    def draw_detections(
        self,
        base_pixmap: QPixmap,
        detections: Dict[str, Any],
        indices: Dict[str, int],
        max_radius_km: float,
    ) -> QPixmap:
        """
        Малює точки виявлених об'єктів на копії базового зображення радара.
        """
        if base_pixmap.isNull():
            return QPixmap()

        result = base_pixmap.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)

        center_x = result.width() / 2.0
        center_y = result.height() / 2.0

        max_px_radius = min(center_x, center_y)

        safe_max_radius_km = max_radius_km if max_radius_km > 0 else 1.0
        scale = max_px_radius / safe_max_radius_km

        for event_id, event in detections.items():
            index = str(indices.get(event_id, "?"))

            pixel_dist = event.distance_km * scale

            is_out_of_bounds = pixel_dist > max_px_radius
            is_on_border = pixel_dist * 1.05 >= max_px_radius - RADAR_POINT_SIZE / 2

            offset_x = 0
            offset_y = RADAR_TEXT_OFFSET_Y_DEFAULT

            if is_out_of_bounds or is_on_border:
                pixel_dist = max_px_radius - RADAR_BORDER_OFFSET

                if (
                    event.angle > RADAR_TEXT_ANGLE_THRESHOLD_HIGH
                    or event.angle < RADAR_TEXT_ANGLE_THRESHOLD_LOW
                ):
                    offset_y = 0
                    offset_x = RADAR_TEXT_OFFSET_CORRECTION

            if is_out_of_bounds:
                pen = QPen(QColor("orange"), RADAR_POINT_SIZE - 2)
            else:
                pen = QPen(QColor("red"), RADAR_POINT_SIZE)

            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            rad_angle = math.radians(event.angle - RADAR_ANGLE_ROTATION_OFFSET)

            x = center_x + pixel_dist * math.cos(rad_angle)
            y = center_y + pixel_dist * math.sin(rad_angle)

            painter.drawPoint(int(x), int(y))

            painter.setPen(QPen(QColor("black"), 1))
            painter.drawText(int(x) + offset_x, int(y) + offset_y, index)

        painter.end()
        return result

    def draw_scan_animation(self, size, has_detections: bool) -> QPixmap:
        """
        Малює прозорий pixmap з обертовим градієнтом (сканером).
        """
        self.radar_angle = (self.radar_angle + 6) % 360

        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPointF(pixmap.width() / 2, pixmap.height() / 2)
        radius = min(pixmap.width(), pixmap.height()) / 2

        gradient = QConicalGradient(center, -self.radar_angle)

        if has_detections:
            gradient.setColorAt(0.0, QColor(215, 40, 30, 100))
            gradient.setColorAt(0.25, QColor(180, 30, 30, 70))
            gradient.setColorAt(1.0, QColor(100, 30, 30, 20))
        else:
            gradient.setColorAt(0.0, QColor(40, 215, 30, 90))
            gradient.setColorAt(0.25, QColor(30, 180, 30, 50))
            gradient.setColorAt(1.0, QColor(30, 100, 30, 10))

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)
        painter.end()

        return pixmap

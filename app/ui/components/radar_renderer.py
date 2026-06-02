import math
from typing import List, Optional

from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import QColor, QConicalGradient, QFont, QPainter, QPen, QPixmap

from app.models.radar_target import RadarTarget

# Константи
RADAR_POINT_SIZE = 20
RADAR_TEXT_OFFSET_Y_DEFAULT = -15
RADAR_TEXT_OFFSET_CORRECTION = 15
RADAR_BORDER_OFFSET = 15
RADAR_ANGLE_ROTATION_OFFSET = 90
RADAR_TEXT_ANGLE_THRESHOLD_LOW = 40
RADAR_TEXT_ANGLE_THRESHOLD_HIGH = 320


class RadarRenderer:
    """Клас відповідає виключно за малювання (Rendering) елементів радара.

    Цей клас інкапсулює всю логіку візуалізації об'єктів на радарній сітці,
    включаючи обробку виходу за межі видимості, запобігання накладанню тексту
    та анімацію сканування.
    """

    def __init__(self) -> None:
        self.radar_angle: int = 0
        self._last_scale: float = 1.0
        self._last_center: tuple[float, float] = (0, 0)
        self._current_targets: List[RadarTarget] = []

    def draw_detections(
        self,
        base_pixmap: QPixmap,
        targets: List[RadarTarget],
        max_radius_km: float,
    ) -> QPixmap:
        """Малює точки виявлених об'єктів на копії базового зображення радара."""
        if base_pixmap.isNull():
            return QPixmap()

        result = base_pixmap.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()

        center_x = result.width() / 2.0
        center_y = result.height() / 2.0

        max_px_radius = min(center_x, center_y)
        safe_max_radius_km = max_radius_km if max_radius_km > 0 else 1.0
        scale = max_px_radius / safe_max_radius_km

        self._last_scale = scale
        self._last_center = (center_x, center_y)
        self._current_targets = targets

        occupied_rects: List[QRect] = []

        sorted_targets = sorted(targets, key=lambda t: t.distance_km)

        for target in sorted_targets:
            index_str = str(target.visual_index)
            pixel_dist = target.distance_km * scale

            is_out_of_bounds = pixel_dist > max_px_radius
            is_on_border = pixel_dist * 1.05 >= max_px_radius - RADAR_POINT_SIZE / 2

            offset_x = 0
            offset_y = RADAR_TEXT_OFFSET_Y_DEFAULT
            correction_applied = False

            if is_out_of_bounds or is_on_border:
                pixel_dist = max_px_radius - RADAR_BORDER_OFFSET
                correction_applied = True

                if (
                    target.angle > RADAR_TEXT_ANGLE_THRESHOLD_HIGH
                    or target.angle < RADAR_TEXT_ANGLE_THRESHOLD_LOW
                ):
                    offset_y = 0
                    offset_x = RADAR_TEXT_OFFSET_CORRECTION

            if is_out_of_bounds:
                pen = QPen(QColor("orange"), RADAR_POINT_SIZE - 2)
            else:
                pen = QPen(QColor("red"), RADAR_POINT_SIZE)

            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            rad_angle = math.radians(target.angle - RADAR_ANGLE_ROTATION_OFFSET)
            x = center_x + pixel_dist * math.cos(rad_angle)
            y = center_y + pixel_dist * math.sin(rad_angle)

            painter.drawPoint(int(x), int(y))

            painter.setPen(QPen(QColor("black"), 1))

            text_w = fm.horizontalAdvance(index_str)
            text_h = fm.height()

            tx = int(x) + offset_x
            ty = int(y) + offset_y

            if not correction_applied:
                ty -= text_h // 4

            text_rect = QRect(tx, ty - text_h, text_w, text_h)

            final_rect = self._resolve_collision(
                text_rect, occupied_rects, result.rect()
            )

            painter.drawText(final_rect.bottomLeft(), index_str)
            occupied_rects.append(final_rect)

        painter.end()
        return result

    def _resolve_collision(
        self, current: QRect, occupied: List[QRect], bounds: QRect
    ) -> QRect:
        """Шукає вільне місце для тексту, зсуваючи його при накладанні."""
        if not bounds.contains(current):
            current = self._fit_in_bounds(current, bounds)

        collision = False
        for rect in occupied:
            if current.intersects(rect):
                collision = True
                break

        if not collision:
            return current

        shifts = [
            (0, -20),
            (0, 20),
            (25, 0),
            (-25, 0),
            (20, -20),
        ]

        original_pos = current.topLeft()

        for dx, dy in shifts:
            current.moveTopLeft(original_pos)
            current.translate(dx, dy)

            if not bounds.contains(current):
                continue

            is_free = True
            for rect in occupied:
                if current.intersects(rect):
                    is_free = False
                    break

            if is_free:
                return current

        current.moveTopLeft(original_pos)
        return current

    def _fit_in_bounds(self, rect: QRect, bounds: QRect) -> QRect:
        """Вписує прямокутник повністю всередині заданих меж."""
        if rect.left() < bounds.left():
            rect.moveLeft(bounds.left())
        if rect.right() > bounds.right():
            rect.moveRight(bounds.right())
        if rect.top() < bounds.top():
            rect.moveTop(bounds.top())
        if rect.bottom() > bounds.bottom():
            rect.moveBottom(bounds.bottom())
        return rect

    def get_target_id_at_position(
        self, click_x: int, click_y: int, tolerance_px: int = 20
    ) -> Optional[int]:
        """Визначає візуальний індекс цілі за координатами кліку."""
        center_x, center_y = self._last_center
        scale = self._last_scale

        closest_target = None
        min_dist = float("inf")

        max_px_radius = min(center_x, center_y)

        for target in self._current_targets:
            pixel_dist = target.distance_km * scale

            if pixel_dist > max_px_radius:
                pixel_dist = max_px_radius - RADAR_BORDER_OFFSET

            rad_angle = math.radians(target.angle - RADAR_ANGLE_ROTATION_OFFSET)

            target_x = center_x + pixel_dist * math.cos(rad_angle)
            target_y = center_y + pixel_dist * math.sin(rad_angle)

            dist_to_click = math.sqrt(
                (click_x - target_x) ** 2 + (click_y - target_y) ** 2
            )

            if dist_to_click <= tolerance_px:
                if dist_to_click < min_dist:
                    min_dist = dist_to_click
                    closest_target = target

        if not closest_target:
            return None

        return closest_target.visual_index

    def draw_scan_animation(self, size, has_detections: bool) -> QPixmap:
        """Малює шар з анімацією обертового променя радара."""
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

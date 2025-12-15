from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QBrush,
    QPolygonF,
    QMouseEvent,
    QPaintEvent,
)
from PyQt6.QtCore import Qt, QPointF, QEvent, QCoreApplication
from datetime import datetime
import math

from app.protocols import ChartWidgetSettings
from app.models.detection_event import DetectionEvent


class LogChartWidget(QWidget):
    """
    Універсальний віджет для малювання різних типів графіків.
    """

    def __init__(self, settings_service: ChartWidgetSettings, parent=None):
        super().__init__(parent)

        self.settings_service = settings_service

        self.setMouseTracking(True)
        self._setup_state_variables()
        # self._load_language()

    def _setup_state_variables(self):
        self.chart_type = "timeline"
        self.data = []
        self.highlight_ids = set()

        self._interactive_points = []

        self.color_bg = QColor(0, 20, 0, 100)
        self.color_grid = QColor(50, 136, 68, 80)
        self.color_rf = QColor(255, 100, 100)
        self.color_sound = QColor(100, 100, 255)
        self.color_highlight = QColor(255, 255, 0)
        self.color_path = QColor(0, 255, 255)
        self.color_text = QColor(200, 200, 200)

    # def _load_language(self):
    #     lang_code = self.settings_service.lang_code

    #     if lang_code == None:
    #         return

    #     QCoreApplication.removeTranslator(self.translator)

    #     path = f"app/i18n/qm/app_{lang_code}.qm"
    #     if self.translator.load(path):
    #         QCoreApplication.installTranslator(self.translator)
    #     else:
    #         print(f"Помилка: не вдалося завантажити {path}")

    def set_data(self, data, highlight_ids: set = None):
        self.data = data
        self.highlight_ids = highlight_ids or set()
        self.update()

    def set_chart_type(self, t: str):
        self.chart_type = t
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Обробка наведення миші для Tooltip."""
        pos = event.pos()
        found = False

        for point, data in self._interactive_points:
            if isinstance(point, QPointF):
                dist = math.sqrt(
                    (pos.x() - point.x()) ** 2 + (pos.y() - point.y()) ** 2
                )
                if dist < 8:
                    self._show_tooltip(event.globalPosition().toPoint(), data)
                    found = True
                    break

        if not found:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def _show_tooltip(self, global_pos: QPointF, data: DetectionEvent):
        """Формує текст підказки."""
        dt = datetime.fromisoformat(data.timestamp)
        time_str = dt.strftime("%H:%M:%S")
        txt = (
            f"<b>{data.name}</b> ({data.object_class})<br>"
            f"Time: {time_str}<br>"
            f"Dist: {data.distance}m, Angle: {data.angle:.0f}°<br>"
            f"Conf: {data.confidence:.2f}<br>"
            f"False alarm: {data.id in self.highlight_ids}<br>"
            f"Type: {data.type}"
        )
        QToolTip.showText(global_pos, txt, self)

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.color_bg)

        self._interactive_points = []

        if not self.data:
            p.setPen(QColor(150, 150, 150))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Немає даних")
            return

        if self.chart_type == "timeline":
            self._draw_timeline(p)
        elif self.chart_type == "bar":
            self._draw_bar(p)
        elif self.chart_type == "path":
            self._draw_polar_path(p)
        elif self.chart_type == "signal":
            self._draw_signal_graph(p)
        elif self.chart_type == "radar_snapshot":
            self._draw_radar_snapshot(p)

    def _draw_timeline(self, p: QPainter):
        w, h = self.width(), self.height()
        margin_left = 60.0
        margin_right = 30.0
        margin_top = 30.0
        margin_bottom = 30.0

        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom

        sorted_data = sorted(self.data, key=lambda x: x.timestamp)
        if not sorted_data:
            return

        t_start = datetime.fromisoformat(sorted_data[0].timestamp).timestamp()
        t_end = datetime.fromisoformat(sorted_data[-1].timestamp).timestamp()
        duration = t_end - t_start or 1

        STEP_DIST = 250

        max_data_dist = max([d.distance for d in sorted_data]) if sorted_data else 1000

        view_max_dist = math.ceil(max_data_dist / STEP_DIST) * STEP_DIST
        if view_max_dist == 0:
            view_max_dist = STEP_DIST

        STEP_TIME = 30 * 60

        first_tick_ts = math.ceil(t_start / STEP_TIME) * STEP_TIME

        grid_pen = QPen(QColor(100, 150, 100, 80))
        grid_pen.setStyle(Qt.PenStyle.DashLine)
        grid_pen.setWidth(1)

        axis_pen = QPen(self.color_grid, 2)
        text_pen = QPen(self.color_text)

        current_dist = 0
        while current_dist <= view_max_dist:
            ratio = current_dist / view_max_dist

            y = (h - margin_bottom) - (ratio * plot_h)

            p.setPen(grid_pen)
            p.drawLine(QPointF(margin_left, y), QPointF(w - margin_right, y))

            p.setPen(text_pen)
            p.drawText(int(margin_left - 45), int(y + 5), f"{current_dist}m")

            current_dist += STEP_DIST

        p.drawText(int(margin_left), int(margin_top - 10), "Distance (m) ▲")

        current_t = first_tick_ts
        while current_t <= t_end:

            ratio = (current_t - t_start) / duration
            x = margin_left + ratio * plot_w

            if 0 <= ratio <= 1:
                p.setPen(grid_pen)
                p.drawLine(QPointF(x, margin_top), QPointF(x, h - margin_bottom))

                dt_label = datetime.fromtimestamp(current_t).strftime("%H:%M")
                p.setPen(text_pen)

                fm = p.fontMetrics()
                tw = fm.horizontalAdvance(dt_label)
                p.drawText(int(x - tw / 2), int(h - margin_bottom + 20), dt_label)

            current_t += STEP_TIME

        p.setPen(axis_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(int(margin_left), int(margin_top), int(plot_w), int(plot_h))

        for ev in sorted_data:
            t_curr = datetime.fromisoformat(ev.timestamp).timestamp()

            x_ratio = (t_curr - t_start) / duration
            x = margin_left + x_ratio * plot_w

            y_ratio = ev.distance / view_max_dist
            y = (h - margin_bottom) - (y_ratio * plot_h)

            color = self.color_rf if ev.type == "RF" else self.color_sound
            if ev.id in self.highlight_ids:
                color = self.color_highlight

            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            pt = QPointF(x, y)

            if margin_left <= x <= (w - margin_right):
                p.drawEllipse(pt, 6, 6)
                self._interactive_points.append((pt, ev))

    def _draw_bar(self, p: QPainter):
        from collections import Counter

        counts = Counter([d.object_class for d in self.data])
        if not counts:
            return

        classes = list(counts.keys())
        values = list(counts.values())
        max_val = max(values)

        w, h = self.width(), self.height()
        margin = 50
        bar_width = (w - 2 * margin) / len(classes) * 0.6
        spacing = (w - 2 * margin) / len(classes)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self.color_grid))

        for i, (cls, val) in enumerate(counts.items()):
            bar_h = (val / max_val) * (h - 2 * margin)
            x = margin + i * spacing + 10
            y = h - margin - bar_h
            p.drawRect(int(x), int(y), int(bar_width), int(bar_h))
            p.setPen(self.color_text)
            p.drawText(int(x), int(y - 5), str(val))
            p.drawText(int(x), int(h - margin + 20), cls)

    def _draw_polar_path(self, p: QPainter):
        w, h = self.width(), self.height()
        center = QPointF(w / 2, h / 2)
        radius = min(w, h) / 2 - 30

        # Сортуємо по часу
        sorted_data = sorted(self.data, key=lambda x: x.timestamp)
        max_dist = max([d.distance for d in sorted_data]) if sorted_data else 1000
        if max_dist < 100:
            max_dist = 100

        p.setPen(QPen(self.color_grid, 1))

        p.drawEllipse(center, radius, radius)
        p.drawEllipse(center, radius * 0.5, radius * 0.5)

        p.drawLine(
            QPointF(center.x(), center.y() - radius),
            QPointF(center.x(), center.y() + radius),
        )
        p.drawLine(
            QPointF(center.x() - radius, center.y()),
            QPointF(center.x() + radius, center.y()),
        )

        # Підписи дистанції
        p.setPen(self.color_text)
        p.setFont(QFont("Arial", 8))
        p.drawText(int(center.x() + 5), int(center.y() - radius + 10), f"{max_dist}m")
        p.drawText(
            int(center.x() + 5),
            int(center.y() - radius * 0.5 + 10),
            f"{int(max_dist/2)}m",
        )
        # ---------------------

        path_points = []
        for d in sorted_data:
            rad = math.radians(d.angle - 90)
            r_px = (d.distance / max_dist) * radius
            x = center.x() + r_px * math.cos(rad)
            y = center.y() + r_px * math.sin(rad)
            pt = QPointF(x, y)
            path_points.append(pt)
            self._interactive_points.append((pt, d))

        if len(path_points) > 1:
            p.setPen(QPen(self.color_path, 2, Qt.PenStyle.DashLine))
            p.drawPolyline(path_points)

        p.setFont(QFont("Arial", 8))
        for i, pt in enumerate(path_points):
            if i == 0 or i == len(path_points) - 1 or i % 5 == 0:

                dt = datetime.fromisoformat(sorted_data[i].timestamp)
                time_str = dt.strftime("%H:%M:%S")
                p.setPen(Qt.PenStyle.NoPen)
                color = (
                    self.color_highlight
                    if i == len(path_points) - 1
                    else self.color_path
                )
                p.setBrush(QBrush(color))
                p.drawEllipse(pt, 4, 4)
                p.setPen(QColor(200, 200, 200))
                p.drawText(int(pt.x() + 5), int(pt.y()), time_str)
            else:
                # Маленькі проміжні точки
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(self.color_path))
                p.drawEllipse(pt, 2, 2)

    def _draw_signal_graph(self, p: QPainter):
        w, h = self.width(), self.height()
        margin = 40.0

        sorted_data = sorted(self.data, key=lambda x: x.timestamp)
        if not sorted_data:
            return

        t_start = datetime.fromisoformat(sorted_data[0].timestamp).timestamp()
        t_end = datetime.fromisoformat(sorted_data[-1].timestamp).timestamp()
        duration = t_end - t_start or 1

        p.setPen(QPen(self.color_grid, 2))
        p.drawLine(QPointF(margin, h - margin), QPointF(w - margin, h - margin))
        p.drawLine(QPointF(margin, margin), QPointF(margin, h - margin))

        # Підписи осей
        p.setPen(self.color_text)
        dt_start = datetime.fromtimestamp(t_start).strftime("%H:%M:%S")
        dt_end = datetime.fromtimestamp(t_end).strftime("%H:%M:%S")
        p.drawText(int(margin), int(h - 5), dt_start)
        p.drawText(int(w - 100), int(h - 5), dt_end)
        p.drawText(5, int(h - margin), "0%")
        p.drawText(5, int(margin), "100%")

        points = []
        for d in sorted_data:
            t_curr = datetime.fromisoformat(d.timestamp).timestamp()
            x = margin + ((t_curr - t_start) / duration) * (w - 2 * margin)
            y = (h - margin) - (d.confidence * (h - 2 * margin))
            pt = QPointF(x, y)
            points.append(pt)
            self._interactive_points.append((pt, d))

        if len(points) > 1:
            p.setPen(QPen(self.color_rf, 2))
            p.drawPolyline(points)
            p.setBrush(QBrush(QColor(255, 100, 100, 50)))
            p.setPen(Qt.PenStyle.NoPen)
            poly_points = (
                [QPointF(margin, h - margin)]
                + points
                + [QPointF(points[-1].x(), h - margin)]
            )
            p.drawPolygon(QPolygonF(poly_points))

            p.setBrush(QBrush(self.color_rf))
            for pt in points:
                p.drawEllipse(pt, 3, 3)

    def _draw_radar_snapshot(self, p: QPainter):
        w, h = self.width(), self.height()
        center = QPointF(w / 2, h / 2)
        radius = min(w, h) / 2 - 30

        p.setPen(QPen(self.color_grid, 1))
        p.drawEllipse(center, radius, radius)
        p.drawEllipse(center, radius * 0.5, radius * 0.5)

        max_dist = max([d.distance for d in self.data]) if self.data else 5000

        p.setPen(self.color_text)
        p.drawText(int(center.x()), int(center.y() - radius - 5), f"{max_dist}m")

        for d in self.data:
            rad = math.radians(d.angle - 90)
            r_px = (d.distance / max_dist) * radius
            x = center.x() + r_px * math.cos(rad)
            y = center.y() + r_px * math.sin(rad)
            pt = QPointF(x, y)

            col = self.color_sound if d.type == "Sound" else self.color_rf
            if d.id in self.highlight_ids:
                col = self.color_highlight

            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            size = 5 + d.confidence * 10
            p.drawEllipse(pt, size, size)

            p.setPen(QColor(255, 255, 255))
            p.drawText(int(x + 5), int(y), d.name)

            self._interactive_points.append((pt, d))

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
from PyQt6.QtCore import Qt, QPointF, QCoreApplication, QTranslator
from datetime import datetime
import math
import numpy as np
from typing import List, Set, Tuple, Optional, Callable

from app.protocols import ChartWidgetSettings
from app.models.detection_event import DetectionEvent


class LogChartWidget(QWidget):
    """
    Універсальний віджет для малювання графіків.
    Всі лінійні графіки тепер мають уніфіковану сітку.
    """

    def __init__(self, settings_service: ChartWidgetSettings, parent=None):
        super().__init__(parent)

        self.settings_service = settings_service
        self.setMouseTracking(True)
        self._setup_style()
        self._setup_state_variables()
        self._load_language()

    def _setup_style(self):
        """Ініціалізація кольорів та стилів."""
        self.color_bg = QColor(0, 20, 0, 100)
        self.color_grid = QColor(50, 136, 68, 100)  # Основні осі
        self.color_grid_faint = QColor(100, 150, 100, 50)  # Пунктирна сітка
        self.color_rf = QColor(255, 100, 100)
        self.color_sound = QColor(100, 100, 255)
        self.color_highlight = QColor(255, 255, 0)
        self.color_path = QColor(0, 255, 255)
        self.color_text = QColor(200, 200, 200)

    def _setup_state_variables(self):
        self.translator = QTranslator()
        self.chart_type: str = "timeline"
        self.data: List[DetectionEvent] = []
        self.highlight_ids: Set[int] = set()
        self._interactive_points: List[Tuple[QPointF, DetectionEvent]] = []

    def _load_language(self):
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)
        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    def set_data(
        self, data: List[DetectionEvent], highlight_ids: Optional[Set[int]] = None
    ):
        self.data = data
        self.highlight_ids = highlight_ids or set()
        self.update()

    def set_chart_type(self, t: str):
        self.chart_type = t
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.pos()
        found = False

        for point, data in self._interactive_points:
            if abs(pos.x() - point.x()) < 10 and abs(pos.y() - point.y()) < 10:
                dist = math.hypot(pos.x() - point.x(), pos.y() - point.y())
                if dist < 8:
                    self._show_tooltip(event.globalPosition().toPoint(), data)
                    found = True
                    break

        if not found:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def _show_tooltip(self, global_pos, data: DetectionEvent):
        dt = datetime.fromisoformat(data.timestamp)
        time_str = dt.strftime("%H:%M:%S")
        is_highlighted = data.id in self.highlight_ids

        txt = (
            f"<b>{data.name}</b> ({data.object_class})<br>"
            f"Time: {time_str}<br>"
            f"Dist: {data.distance}m, Angle: {data.angle:.0f}°<br>"
            f"Conf: {data.confidence:.2f}<br>"
            f"False alarm: {is_highlighted}<br>"
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

        if self.chart_type in ["path", "radar_snapshot"]:
            self._draw_polar_chart(p, mode=self.chart_type)
        elif self.chart_type in ["timeline", "signal"]:
            self._draw_cartesian_chart(p, mode=self.chart_type, num_ticks=20)
        elif self.chart_type == "bar":
            self._draw_bar(p)

    def _draw_polar_chart(self, p: QPainter, mode: str):
        w, h = self.width(), self.height()
        center = QPointF(w / 2, h / 2)
        radius = min(w, h) / 2 - 30

        sorted_data = sorted(self.data, key=lambda x: x.timestamp)
        max_dist_val = max([d.distance for d in sorted_data]) if sorted_data else 1000

        scale_step = 500
        if max_dist_val < 100:
            scale_step = 100
        view_max_dist = math.ceil(max_dist_val / scale_step) * scale_step
        if view_max_dist == 0:
            view_max_dist = scale_step

        self._draw_polar_grid(p, center, radius, view_max_dist)

        if mode == "path":
            self._draw_polar_path_content(p, sorted_data, center, radius, view_max_dist)
        elif mode == "radar_snapshot":
            self._draw_radar_points_content(
                p, sorted_data, center, radius, view_max_dist
            )

    def _draw_polar_grid(
        self, p: QPainter, center: QPointF, radius: float, max_dist: int
    ):
        for i in np.arange(0.2, 1.2, 0.2):
            p.setPen(QPen(self.color_grid, 1))
            r_current = radius * i
            p.drawEllipse(center, r_current, r_current)

            p.setPen(self.color_text)
            p.setFont(QFont("Arial", 8))
            p.drawText(
                int(center.x() + 5),
                int(center.y() - r_current + 10),
                f"{int(max_dist * i)}m",
            )

        p.setPen(QPen(self.color_grid, 1))
        p.drawLine(
            QPointF(center.x(), center.y() - radius * 1.1),
            QPointF(center.x(), center.y() + radius * 1.1),
        )
        p.drawLine(
            QPointF(center.x() - radius * 1.1, center.y()),
            QPointF(center.x() + radius * 1.1, center.y()),
        )

    def _get_polar_pos(
        self, center: QPointF, radius: float, angle: float, dist: float, max_dist: float
    ) -> QPointF:
        rad = math.radians(angle - 90)
        r_px = (dist / max_dist) * radius
        x = center.x() + r_px * math.cos(rad)
        y = center.y() + r_px * math.sin(rad)
        return QPointF(x, y)

    def _draw_polar_path_content(
        self,
        p: QPainter,
        data: List[DetectionEvent],
        center: QPointF,
        radius: float,
        max_dist: int,
    ):
        path_points = []
        for d in data:
            pt = self._get_polar_pos(center, radius, d.angle, d.distance, max_dist)
            path_points.append(pt)
            self._interactive_points.append((pt, d))

        if len(path_points) > 1:
            p.setPen(QPen(self.color_path, 2, Qt.PenStyle.DashLine))
            p.drawPolyline(path_points)

        p.setFont(QFont("Arial", 8))
        for i, pt in enumerate(path_points):
            is_key_point = i == 0 or i == len(path_points) - 1 or i % 5 == 0
            if is_key_point:
                dt = datetime.fromisoformat(data[i].timestamp)
                time_str = dt.strftime("%H:%M:%S")

                p.setPen(Qt.PenStyle.NoPen)
                color = (
                    self.color_highlight
                    if i == len(path_points) - 1
                    else self.color_path
                )
                p.setBrush(QBrush(color))
                p.drawEllipse(pt, 4, 4)

                p.setPen(self.color_text)
                p.drawText(int(pt.x() - 20), int(pt.y() - 10), time_str)
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(self.color_path))
                p.drawEllipse(pt, 2, 2)

    def _draw_radar_points_content(
        self,
        p: QPainter,
        data: List[DetectionEvent],
        center: QPointF,
        radius: float,
        max_dist: int,
    ):
        for d in data:
            pt = self._get_polar_pos(center, radius, d.angle, d.distance, max_dist)
            col = self.color_sound if d.type == "Sound" else self.color_rf
            if d.id in self.highlight_ids:
                col = self.color_highlight

            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            size = 3 + d.confidence * 4
            p.drawEllipse(pt, size, size)

            p.setPen(QColor(255, 255, 255))
            p.drawText(int(pt.x() + 5), int(pt.y()), d.name)
            self._interactive_points.append((pt, d))

    def _draw_cartesian_chart(self, p: QPainter, mode: str, num_ticks: int = 20):
        """
        Єдина функція для Timeline та Signal.
        """
        w, h = self.width(), self.height()
        margin_left = 60.0
        margin_right = 30.0
        margin_top = 30.0
        margin_bottom = 30.0

        plot_rect = (
            margin_left,
            margin_top,
            w - margin_left - margin_right,
            h - margin_top - margin_bottom,
        )
        (px, py, pw, ph) = plot_rect

        sorted_data = sorted(self.data, key=lambda x: x.timestamp)
        if not sorted_data:
            return

        # X Axis (Time) calculation
        t_start = datetime.fromisoformat(sorted_data[0].timestamp).timestamp()
        t_end = datetime.fromisoformat(sorted_data[-1].timestamp).timestamp()
        duration = t_end - t_start or 1

        # Y Axis calculation (Unification logic)
        y_max = 1.0
        label_formatter = lambda v: f"{int(v*100)}%"

        if mode == "timeline":
            max_data_dist = (
                max([d.distance for d in sorted_data]) if sorted_data else 1000
            )
            y_max = math.ceil(max_data_dist / 1000) * 1000
            if y_max == 0:
                y_max = 1000
            label_formatter = lambda v: f"{int(v)}m"
        else:
            y_max = 1.0

        # 1. Спільна сітка
        self._draw_cartesian_grid(
            p, plot_rect, y_max, t_start, t_end, duration, num_ticks, label_formatter
        )

        # 2. Малювання даних
        points_signal = []

        for ev in sorted_data:
            t_curr = datetime.fromisoformat(ev.timestamp).timestamp()
            x_ratio = (t_curr - t_start) / duration
            x = px + x_ratio * pw

            val_y = ev.distance if mode == "timeline" else ev.confidence
            norm_y = val_y / y_max

            # Clamp щоб не вилізло за графік
            norm_y = max(0, min(1, norm_y))

            y = (py + ph) - (norm_y * ph)
            pt = QPointF(x, y)

            if mode == "timeline":
                if px <= x <= (px + pw):
                    color = self.color_rf if ev.type == "RF" else self.color_sound
                    if ev.id in self.highlight_ids:
                        color = self.color_highlight
                    p.setBrush(QBrush(color))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(pt, 6, 6)
                    self._interactive_points.append((pt, ev))
            else:
                points_signal.append(pt)
                self._interactive_points.append((pt, ev))

        if mode == "signal" and points_signal:
            self._draw_signal_poly(p, points_signal, plot_rect)

    def _draw_cartesian_grid(
        self,
        p: QPainter,
        rect,
        y_max_val,
        t_start,
        t_end,
        duration,
        num_ticks,
        label_formatter,
    ):
        """
        Уніфікована сітка:
        - Y: ділиться на num_ticks частин (пунктир).
        - X: часові мітки (динамічний крок, як в timeline).
        """
        (px, py, pw, ph) = rect

        p.setFont(QFont("Arial", 8))
        grid_pen = QPen(self.color_grid_faint)
        grid_pen.setStyle(Qt.PenStyle.DashLine)

        # --- Y Axis (Horizontal Lines) ---
        for i in range(num_ticks + 1):
            ratio = i / num_ticks
            y = (py + ph) - (ratio * ph)
            val = ratio * y_max_val

            p.setPen(grid_pen)
            p.drawLine(QPointF(px, y), QPointF(px + pw, y))

            if num_ticks > 10 and i % 2 != 0:
                continue  # Підписуємо тільки парні

            p.setPen(self.color_text)
            txt = label_formatter(val)
            # Вирівнювання тексту
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(txt)
            p.drawText(int(px - tw - 5), int(y + 4), txt)

        # Розраховуємо крок як десяту частину
        step_time = math.ceil((duration / 60) / 10) * 60

        first_tick_ts = math.ceil(t_start / step_time) * step_time
        current_t = first_tick_ts

        while current_t <= t_end:
            ratio = (current_t - t_start) / duration
            x = px + ratio * pw

            if 0 <= ratio <= 1:
                p.setPen(grid_pen)
                p.drawLine(QPointF(x, py), QPointF(x, py + ph))

                dt_label = datetime.fromtimestamp(current_t).strftime("%H:%M")
                p.setPen(self.color_text)
                tw = p.fontMetrics().horizontalAdvance(dt_label)
                p.drawText(int(x - tw / 2), int(py + ph + 20), dt_label)

            current_t += step_time

        # Рамка графіка (осі)
        p.setPen(QPen(self.color_grid, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)

        p.drawRect(int(px), int(py), int(pw), int(ph))

        # Підпис осі Y зверху
        p.setPen(self.color_text)
        title = "Distance ▲" if "m" in label_formatter(0) else "Confidence ▲"
        p.drawText(int(px), int(py - 10), title)

    def _draw_signal_poly(self, p: QPainter, points: List[QPointF], rect):
        """Специфічне малювання для Signal (лінія + заливка)."""
        (px, py, pw, ph) = rect

        p.setPen(QPen(self.color_rf, 2))
        p.drawPolyline(points)

        p.setBrush(QBrush(QColor(255, 100, 100, 50)))
        p.setPen(Qt.PenStyle.NoPen)
        poly_points = (
            [QPointF(px, py + ph)] + points + [QPointF(points[-1].x(), py + ph)]
        )
        p.drawPolygon(QPolygonF(poly_points))

        # Точки
        p.setBrush(QBrush(self.color_rf))
        for pt in points:
            p.drawEllipse(pt, 3, 3)

    def _draw_bar(self, p: QPainter):
        from collections import Counter

        counts = Counter([d.object_class for d in self.data])
        if not counts:
            return

        sorted_counts = Counter(dict(counts.most_common()))

        classes = list(sorted_counts.keys())
        values = list(sorted_counts.values())
        max_val = max(values)

        w, h = self.width(), self.height()
        margin = 40

        avail_w = w - 2 * margin
        avail_h = h - 2 * margin

        bar_width = avail_w / len(classes) * 0.6
        spacing = avail_w / len(classes)

        p.setBrush(QBrush(self.color_grid))
        p.setPen(self.color_text)

        for i, (cls, val) in enumerate(sorted_counts.items()):

            bar_h = (val / max_val) * avail_h
            x = margin + i * spacing
            y = h - margin - bar_h

            p.drawRect(int(x), int(y), int(bar_width), int(bar_h))

            p.drawText(int(x), int(y - 5), str(val))
            p.drawText(int(x), int(h - margin + 20), cls)

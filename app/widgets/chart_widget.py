from datetime import datetime
import math
from typing import List, Set, Tuple, Optional, Dict
from collections import Counter

import numpy as np
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
    QPainterPath,
)
from PyQt6.QtCore import Qt, QPointF, QCoreApplication, QTranslator

from app.protocols import ChartWidgetSettings
from app.models.detection_event import DetectionEvent


class ChartWidget(QWidget):
    # --- КОНСТАНТИ ВІЗУАЛІЗАЦІЇ ---
    LINE_WIDTH_NORMAL = 3
    LINE_WIDTH_THIN = 1
    DOT_RADIUS = 3

    HIGHLIGHT_RADIUS_OFFSET = 3
    HIGHLIGHT_FRAME_WIDTH = 2

    TEXT_OFFSET_Y = -10
    TIME_DIFF_S = 60

    def __init__(
        self, settings_service: ChartWidgetSettings, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)

        self.settings_service = settings_service
        self.setMouseTracking(True)
        self._setup_style()
        self._setup_state_variables()
        self._load_language()

    def _setup_style(self) -> None:
        self.color_bg = QColor(0, 20, 0, 100)
        self.color_grid = QColor(50, 136, 68, 100)
        self.color_grid_faint = QColor(100, 150, 100, 50)

        self.color_highlight = QColor(255, 255, 0)
        self.color_text = QColor(200, 200, 200)

    def _setup_state_variables(self) -> None:
        self.translator = QTranslator()
        self.chart_type: str = "timeline"
        self.data: List[DetectionEvent] = []
        self.highlight_ids: Set[str] = set()

        self._id_color_cache: Dict[str, QColor] = {}
        self._interactive_points: List[Tuple[QPointF, DetectionEvent]] = []

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)
        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)

    def set_data(
        self, data: List[DetectionEvent], highlight_ids: Optional[Set[str]] = None
    ) -> None:
        self.data = sorted(data, key=lambda x: x.timestamp)
        self.highlight_ids = highlight_ids or set()

        self.update()

    def set_chart_type(self, t: str) -> None:
        self.chart_type = t
        self.update()

    def _get_color_for_id(self, obj_id: str) -> QColor:
        """
        Генерує максимально відмінний колір, використовуючи золотий кут.
        Гарантує, що сусіди не будуть схожими.
        """
        if obj_id in self._id_color_cache:
            return self._id_color_cache[obj_id]

        idx = len(self._id_color_cache)

        hue = int((idx * 137.508) % 360)

        color = QColor.fromHsv(hue, 200, 255)

        self._id_color_cache[obj_id] = color
        return color

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()
        found = False

        for point, data in self._interactive_points:
            if abs(pos.x() - point.x()) < 15 and abs(pos.y() - point.y()) < 15:
                dist = math.hypot(pos.x() - point.x(), pos.y() - point.y())
                if dist < 10:
                    self._show_tooltip(event.globalPosition().toPoint(), data)
                    found = True
                    break

        if not found:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def _show_tooltip(self, global_pos, data: DetectionEvent) -> None:
        dt = datetime.fromisoformat(data.timestamp)
        time_str = dt.strftime("%H:%M:%S")
        is_highlighted = data.id in self.highlight_ids

        txt = (
            f"<b>{data.name}</b> ({data.object_class})<br>"
            f"Time: {time_str}<br>"
            f"Dist: {data.distance}m, Angle: {data.angle:.0f}°<br>"
            f"Conf: {data.confidence:.2f}<br>"
            f"Type: {data.type}<br>"
            f"ID: {data.id[:8]}..."
        )
        if is_highlighted:
            txt += "<br><b style='color:yellow'>HIGHLIGHTED (False Alarm)</b>"

        QToolTip.showText(global_pos, txt, self)

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.color_bg)

        self._interactive_points = []

        if not self.data:
            p.setPen(QColor(150, 150, 150))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Data")
            return

        if self.chart_type in ["path", "radar_snapshot"]:
            self._draw_polar_chart(p, mode=self.chart_type)
        elif self.chart_type in ["timeline", "signal"]:
            self._draw_cartesian_chart(p, mode=self.chart_type, num_ticks=20)
        elif self.chart_type == "bar":
            self._draw_bar(p)

    # -------------------------------------------------------------------------
    # POLAR CHART
    # -------------------------------------------------------------------------
    def _draw_polar_chart(self, p: QPainter, mode: str) -> None:
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
        self._draw_radar_content(p, sorted_data, center, radius, view_max_dist)

    def _draw_polar_grid(
        self, p: QPainter, center: QPointF, radius: float, max_dist: int
    ) -> None:
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
        if r_px > radius:
            r_px = radius
        x = center.x() + r_px * math.cos(rad)
        y = center.y() + r_px * math.sin(rad)
        return QPointF(x, y)

    def _draw_radar_content(
        self,
        p: QPainter,
        data: List[DetectionEvent],
        center: QPointF,
        radius: float,
        max_dist: int,
    ) -> None:
        grouped_data: Dict[str, List[DetectionEvent]] = {}
        for d in data:
            if d.id not in grouped_data:
                grouped_data[d.id] = []
            grouped_data[d.id].append(d)

        for obj_id, events in grouped_data.items():
            if not events:
                continue

            line_color = self._get_color_for_id(obj_id)
            is_highlighted = events[-1].id in self.highlight_ids

            points: List[QPointF] = []
            timestamps: List[float] = []

            for ev in events:
                pt = self._get_polar_pos(
                    center, radius, ev.angle, ev.distance, max_dist
                )
                points.append(pt)
                timestamps.append(datetime.fromisoformat(ev.timestamp).timestamp())
                self._interactive_points.append((pt, ev))

            if len(points) > 1:
                pen_solid = QPen(line_color, self.LINE_WIDTH_NORMAL)
                pen_solid.setCapStyle(Qt.PenCapStyle.RoundCap)

                pen_dash = QPen(line_color, self.LINE_WIDTH_THIN)
                pen_dash.setStyle(Qt.PenStyle.DotLine)

                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i + 1]
                    t1 = timestamps[i]
                    t2 = timestamps[i + 1]

                    if (t2 - t1) > self.TIME_DIFF_S:
                        p.setPen(pen_dash)
                        p.drawLine(p1, p2)
                    else:
                        p.setPen(pen_solid)
                        p.drawLine(p1, p2)

                # --- Маркери (початок/кінець) ---
                start_pt = points[0]
                end_pt = points[-1]

                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(0, 255, 0)))
                p.drawEllipse(start_pt, self.DOT_RADIUS, self.DOT_RADIUS)

                p.setBrush(QBrush(QColor(255, 50, 50)))
                p.drawEllipse(end_pt, self.DOT_RADIUS + 1, self.DOT_RADIUS + 1)

                # --- Підсвітка ТІЛЬКИ на останній точці  ---
                if is_highlighted:
                    p.setPen(QPen(self.color_highlight, self.HIGHLIGHT_FRAME_WIDTH))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    radius_hl = self.DOT_RADIUS + self.HIGHLIGHT_RADIUS_OFFSET
                    p.drawEllipse(end_pt, radius_hl, radius_hl)

                # --- Текст імені посередині лінії ---
                mid_idx = len(points) // 2
                if len(points) > 2:
                    p_a = points[mid_idx - 1]
                    p_b = points[mid_idx]
                else:
                    p_a = start_pt
                    p_b = end_pt

                mid_x = (p_a.x() + p_b.x()) / 2
                mid_y = (p_a.y() + p_b.y()) / 2

                dx = p_b.x() - p_a.x()
                dy = p_b.y() - p_a.y()
                angle_deg = math.degrees(math.atan2(dy, dx))

                if 90 < abs(angle_deg) <= 180:
                    angle_deg += 180

                name_txt = events[0].name
                if len(name_txt) > 10:
                    name_txt = name_txt[:10] + ".."

                p.save()
                p.translate(mid_x, mid_y)
                p.rotate(angle_deg)

                text_col = self.color_highlight if is_highlighted else self.color_text
                p.setPen(text_col)

                p.setFont(QFont("Arial", 8, QFont.Weight.Bold))
                p.drawText(0, self.TEXT_OFFSET_Y, name_txt)
                p.restore()

            else:
                # Одна точка
                pt = points[0]
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(line_color))
                p.drawEllipse(pt, self.DOT_RADIUS, self.DOT_RADIUS)

                text_col = self.color_highlight if is_highlighted else self.color_text
                p.setPen(text_col)
                p.drawText(int(pt.x() + 8), int(pt.y()), events[0].name)

                if is_highlighted:
                    p.setPen(QPen(self.color_highlight, self.HIGHLIGHT_FRAME_WIDTH))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    radius_hl = self.DOT_RADIUS + self.HIGHLIGHT_RADIUS_OFFSET
                    p.drawEllipse(pt, radius_hl, radius_hl)

    # -------------------------------------------------------------------------
    # CARTESIAN CHART (Timeline)
    # -------------------------------------------------------------------------
    def _draw_cartesian_chart(
        self, p: QPainter, mode: str, num_ticks: int = 20
    ) -> None:
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

        t_start = datetime.fromisoformat(sorted_data[0].timestamp).timestamp()
        t_end = datetime.fromisoformat(sorted_data[-1].timestamp).timestamp()
        duration = t_end - t_start or 1

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

        self._draw_cartesian_grid(
            p, plot_rect, y_max, t_start, t_end, duration, num_ticks, label_formatter
        )

        grouped_data: Dict[str, List[DetectionEvent]] = {}
        for d in sorted_data:
            if d.id not in grouped_data:
                grouped_data[d.id] = []
            grouped_data[d.id].append(d)

        for obj_id, events in grouped_data.items():
            if not events:
                continue

            line_color = self._get_color_for_id(obj_id)
            is_highlighted = events[-1].id in self.highlight_ids

            points: List[QPointF] = []
            timestamps: List[float] = []

            for ev in events:
                t_curr = datetime.fromisoformat(ev.timestamp).timestamp()
                x_ratio = (t_curr - t_start) / duration
                x = px + x_ratio * pw

                val_y = ev.distance if mode == "timeline" else ev.confidence
                norm_y = val_y / y_max
                norm_y = max(0, min(1, norm_y))
                y = (py + ph) - (norm_y * ph)

                pt = QPointF(x, y)
                points.append(pt)
                timestamps.append(t_curr)
                self._interactive_points.append((pt, ev))

            if len(points) > 1:
                pen_solid = QPen(line_color, self.LINE_WIDTH_NORMAL)
                pen_dash = QPen(line_color, self.LINE_WIDTH_THIN)
                pen_dash.setStyle(Qt.PenStyle.DotLine)

                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i + 1]
                    t1 = timestamps[i]
                    t2 = timestamps[i + 1]

                    if (t2 - t1) > self.TIME_DIFF_S:
                        p.setPen(pen_dash)
                        p.drawLine(p1, p2)
                    else:
                        p.setPen(pen_solid)
                        p.drawLine(p1, p2)

                # Підсвітка ТІЛЬКИ останньої точки на таймлайні
                if is_highlighted:
                    end_pt = points[-1]
                    p.setPen(QPen(self.color_highlight, self.HIGHLIGHT_FRAME_WIDTH))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    radius_hl = self.DOT_RADIUS + self.HIGHLIGHT_RADIUS_OFFSET
                    p.drawEllipse(end_pt, radius_hl, radius_hl)

            else:
                pt = points[0]
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(line_color))
                p.drawEllipse(pt, self.DOT_RADIUS, self.DOT_RADIUS)

                if is_highlighted:
                    p.setPen(QPen(self.color_highlight, self.HIGHLIGHT_FRAME_WIDTH))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    radius_hl = self.DOT_RADIUS + self.HIGHLIGHT_RADIUS_OFFSET
                    p.drawEllipse(pt, radius_hl, radius_hl)

    def _draw_cartesian_grid(
        self,
        p: QPainter,
        rect: Tuple[float, float, float, float],
        y_max_val: float,
        t_start: float,
        t_end: float,
        duration: float,
        num_ticks: int,
        label_formatter: callable,
    ) -> None:
        (px, py, pw, ph) = rect

        p.setFont(QFont("Arial", 8))
        grid_pen = QPen(self.color_grid_faint)
        grid_pen.setStyle(Qt.PenStyle.DashLine)

        # Y Axis
        for i in range(num_ticks + 1):
            ratio = i / num_ticks
            y = (py + ph) - (ratio * ph)
            val = ratio * y_max_val

            p.setPen(grid_pen)
            p.drawLine(QPointF(px, y), QPointF(px + pw, y))

            if num_ticks > 10 and i % 2 != 0:
                continue

            p.setPen(self.color_text)
            txt = label_formatter(val)
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(txt)
            p.drawText(int(px - tw - 5), int(y + 4), txt)

        # X Axis
        step_time = math.ceil((duration / 60) / 10) * 60
        if step_time == 0:
            step_time = 60

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

        p.setPen(QPen(self.color_grid, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(int(px), int(py), int(pw), int(ph))

        p.setPen(self.color_text)
        title = "Distance ▲" if "m" in label_formatter(0) else "Confidence ▲"
        p.drawText(int(px), int(py - 10), title)

    def _draw_bar(self, p: QPainter) -> None:
        if not self.data:
            return

        unique_objects_map = {}
        for d in self.data:
            unique_objects_map[d.id] = d.object_class

        counts = Counter(unique_objects_map.values())

        if not counts:
            return

        sorted_counts = dict(counts.most_common())

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

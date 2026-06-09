import math
from collections import Counter
from datetime import datetime
from typing import Dict, List

from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen

from app.core.chart_theme import ChartTheme
from app.core.mixins import TranslatorMixin
from app.models.detection_event import DetectionEvent
from app.utils.chart_math import ChartMath


class StandardChartRenderer(TranslatorMixin):
    """
    Рендерер для Timeline, Radar (Polar) та Bar chart.
    Логіка відображення ідентична оригінальному StaticChartWidget.
    """

    def __init__(self):
        self._id_color_cache: Dict[str, QColor] = {}

        # Константи з оригіналу
        self.LINE_WIDTH_NORMAL = 3
        self.LINE_WIDTH_THIN = 1
        self.DOT_RADIUS = 3
        self.HIGHLIGHT_RADIUS_OFFSET = 3
        self.HIGHLIGHT_FRAME_WIDTH = 2
        self.TEXT_OFFSET_Y = -10
        self.TIME_DIFF_S = 60

    def render_polar(
        self,
        p: QPainter,
        full_rect: QRect,
        data: List[DetectionEvent],
        highlight_ids: set,
        interactive_points: list,
    ) -> None:
        """Малює Radar/Path chart."""
        if not data:
            return

        w, h = full_rect.width(), full_rect.height()
        center = QPointF(w / 2, h / 2)
        radius = min(w, h) / 2 - 30

        sorted_data = sorted(data, key=lambda x: x.timestamp)
        max_dist_val = max([d.distance_km for d in sorted_data]) if sorted_data else 1.0

        # --- FIX: Додаємо 10% запасу ---
        max_dist_val *= 1.1

        view_max_dist, step, _ = ChartMath.calculate_nice_axis(
            max_dist_val, target_ticks=5
        )

        self._draw_polar_grid(p, center, radius, view_max_dist, step)

        grouped_data = self._group_by_id(data)
        for obj_id, events in grouped_data.items():
            if not events:
                continue

            line_color = ChartMath.get_color_for_id(obj_id, self._id_color_cache)
            points = []
            timestamps = []

            for ev in events:
                pt = self._get_polar_pos(
                    center, radius, ev.angle, ev.distance_km, view_max_dist
                )
                points.append(pt)
                timestamps.append(datetime.fromisoformat(ev.timestamp).timestamp())
                interactive_points.append((pt, ev))

            self._draw_trace(
                p,
                points,
                timestamps,
                line_color,
                events,
                highlight_ids,
                draw_label=True,
            )

    def render_cartesian(
        self,
        p: QPainter,
        full_rect: QRect,
        data: List[DetectionEvent],
        mode: str,
        highlight_ids: set,
        interactive_points: list,
    ) -> None:
        """Малює Timeline або Signal chart."""
        if not data:
            return

        w, h = full_rect.width(), full_rect.height()

        # --- ORIGINAL MARGINS ---
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

        sorted_data = sorted(data, key=lambda x: x.timestamp)
        t_start = datetime.fromisoformat(sorted_data[0].timestamp).timestamp()
        t_end = datetime.fromisoformat(sorted_data[-1].timestamp).timestamp()
        duration = t_end - t_start or 1.0
        nice_step: float | None = None

        if mode == "timeline":
            max_data_dist = (
                max([d.distance_km for d in sorted_data]) if sorted_data else 1.0
            )
            y_max, nice_step, actual_ticks = ChartMath.calculate_nice_axis(
                max_data_dist, target_ticks=10
            )
            num_ticks = actual_ticks
        else:
            y_max = 1.0
            num_ticks = 10

        def label_formatter(v):
            if mode == "timeline":
                if nice_step and nice_step < 1:
                    return self.tr("{:.1f}km").format(v)
                return self.tr("{}km").format(int(v))
            else:
                return self.tr("{}%").format(int(v * 100))

        self._draw_cartesian_grid(
            p, plot_rect, y_max, t_start, t_end, duration, num_ticks, label_formatter
        )

        grouped_data = self._group_by_id(sorted_data)
        for obj_id, events in grouped_data.items():
            if not events:
                continue

            line_color = ChartMath.get_color_for_id(obj_id, self._id_color_cache)
            points = []
            timestamps = []

            for ev in events:
                t_curr = datetime.fromisoformat(ev.timestamp).timestamp()
                x_ratio = (t_curr - t_start) / duration

                x = px + x_ratio * pw
                val_y = ev.distance_km if mode == "timeline" else ev.confidence
                norm_y = val_y / y_max
                norm_y = max(0, min(1, norm_y))
                y = (py + ph) - (norm_y * ph)

                pt = QPointF(x, y)
                points.append(pt)
                timestamps.append(t_curr)
                interactive_points.append((pt, ev))

            self._draw_trace(
                p,
                points,
                timestamps,
                line_color,
                events,
                highlight_ids,
                draw_label=False,
            )

    def render_bar(
        self, p: QPainter, full_rect: QRect, data: List[DetectionEvent]
    ) -> None:
        """Малює Bar chart."""
        if not data:
            return

        # --- FIX: Group by Object ID first ---
        unique_objects = {}
        for d in data:
            # Якщо id повторюється, ми просто перезаписуємо (або беремо останній/перший клас)
            # Головне, що один ID рахується один раз
            unique_objects[d.id] = d.object_class

        # Тепер рахуємо класи по унікальних об'єктах
        counts = Counter(unique_objects.values())

        if not counts:
            return

        sorted_counts = dict(counts.most_common())

        keys = list(sorted_counts.keys())
        values = list(sorted_counts.values())
        max_val = max(values) if values else 1

        w, h = full_rect.width(), full_rect.height()
        margin = 40
        avail_w = w - 2 * margin
        avail_h = h - 2 * margin

        bar_width = avail_w / len(keys) * 0.6
        spacing = avail_w / len(keys)

        p.setBrush(QBrush(ChartTheme.GRID))
        p.setPen(ChartTheme.TEXT)

        for i, (cls, val) in enumerate(sorted_counts.items()):
            bar_h = (val / max_val) * avail_h
            x = margin + i * spacing + (spacing - bar_width) / 2
            y = h - margin - bar_h

            p.drawRect(int(x), int(y), int(bar_width), int(bar_h))
            p.drawText(int(x), int(y - 5), str(val))
            p.drawText(int(x), int(h - margin + 20), cls)

    # --- INTERNAL HELPERS (Exact copy logic) ---

    def _group_by_id(
        self, data: List[DetectionEvent]
    ) -> Dict[str, List[DetectionEvent]]:
        grouped: Dict[str, List[DetectionEvent]] = {}
        for d in data:
            if d.id not in grouped:
                grouped[d.id] = []
            grouped[d.id].append(d)
        return grouped

    def _get_polar_pos(
        self, center: QPointF, radius: float, angle: float, dist: float, max_dist: float
    ) -> QPointF:
        rad = math.radians(angle - 90)
        # Оригінальна логіка кліпінгу точок
        r_px = (dist / max_dist) * radius
        if r_px > radius:
            r_px = radius
        return QPointF(
            center.x() + r_px * math.cos(rad), center.y() + r_px * math.sin(rad)
        )

    def _draw_trace(
        self,
        p: QPainter,
        points: List[QPointF],
        timestamps: List[float],
        color: QColor,
        events: List[DetectionEvent],
        highlight_ids: set,
        draw_label: bool,
    ):
        if not points:
            return

        is_highlighted = events[-1].id in highlight_ids

        pen_solid = QPen(color, self.LINE_WIDTH_NORMAL)
        pen_solid.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_dash = QPen(color, self.LINE_WIDTH_THIN)
        pen_dash.setStyle(Qt.PenStyle.DotLine)

        if len(points) > 1:
            for i in range(len(points) - 1):
                t1 = timestamps[i]
                t2 = timestamps[i + 1]
                if (t2 - t1) > self.TIME_DIFF_S:
                    p.setPen(pen_dash)
                else:
                    p.setPen(pen_solid)
                p.drawLine(points[i], points[i + 1])

            start_pt = points[0]
            end_pt = points[-1]

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(0, 255, 0)))
            p.drawEllipse(start_pt, self.DOT_RADIUS, self.DOT_RADIUS)

            p.setBrush(QBrush(QColor(255, 50, 50)))
            p.drawEllipse(end_pt, self.DOT_RADIUS + 1, self.DOT_RADIUS + 1)

            if is_highlighted:
                p.setPen(QPen(ChartTheme.HIGHLIGHT, self.HIGHLIGHT_FRAME_WIDTH))
                p.setBrush(Qt.BrushStyle.NoBrush)
                radius_hl = self.DOT_RADIUS + self.HIGHLIGHT_RADIUS_OFFSET
                p.drawEllipse(end_pt, radius_hl, radius_hl)

            if draw_label:
                self._draw_label_rotated(p, points, events[0].name, is_highlighted)
        else:
            pt = points[0]
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            p.drawEllipse(pt, self.DOT_RADIUS, self.DOT_RADIUS)

            text_col = ChartTheme.HIGHLIGHT if is_highlighted else ChartTheme.TEXT
            p.setPen(text_col)
            # p.drawText(int(pt.x() + 8), int(pt.y()), events[0].name)

            if is_highlighted:
                p.setPen(QPen(ChartTheme.HIGHLIGHT, self.HIGHLIGHT_FRAME_WIDTH))
                p.setBrush(Qt.BrushStyle.NoBrush)
                radius_hl = self.DOT_RADIUS + self.HIGHLIGHT_RADIUS_OFFSET
                p.drawEllipse(pt, radius_hl, radius_hl)

    def _draw_label_rotated(self, p, points, text, is_highlighted):
        mid_idx = len(points) // 2
        start_pt = points[0]
        end_pt = points[-1]
        p_a = points[mid_idx - 1] if len(points) > 2 else start_pt
        p_b = points[mid_idx] if len(points) > 2 else end_pt

        mid_x = (p_a.x() + p_b.x()) / 2
        mid_y = (p_a.y() + p_b.y()) / 2

        dx = p_b.x() - p_a.x()
        dy = p_b.y() - p_a.y()
        angle_deg = math.degrees(math.atan2(dy, dx))
        if 90 < abs(angle_deg) <= 180:
            angle_deg += 180

        if len(text) > 10:
            text = text[:10] + ".."

        p.save()
        p.translate(mid_x, mid_y)
        p.rotate(angle_deg)
        text_col = ChartTheme.HIGHLIGHT if is_highlighted else ChartTheme.TEXT
        p.setPen(text_col)
        p.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        p.drawText(0, self.TEXT_OFFSET_Y, text)
        p.restore()

    def _draw_polar_grid(self, p, center, radius, max_dist, step):
        main_pen = QPen(ChartTheme.GRID, 1)
        sub_color = QColor(ChartTheme.GRID)
        sub_color.setAlpha(40)
        sub_pen = QPen(sub_color, 1)
        sub_pen.setStyle(Qt.PenStyle.DotLine)
        p.setFont(QFont("Arial", 8))

        num_steps = int(max_dist / step)
        total_sub_steps = num_steps * 2

        for i in range(1, total_sub_steps + 1):
            val = i * (step / 2)
            if val > max_dist:
                break
            r_current = (val / max_dist) * radius
            is_main = abs(val % step) < 0.001 or abs((val % step) - step) < 0.001

            if is_main:
                p.setPen(main_pen)
                p.drawEllipse(center, r_current, r_current)
                p.setPen(ChartTheme.TEXT)
                p.drawText(
                    int(center.x() + 5),
                    int(center.y() - r_current + 10),
                    (
                        self.tr("{:.1f}km").format(val)
                        if step < 1
                        else self.tr("{}km").format(int(val))
                    ),
                )
            else:
                p.setPen(sub_pen)
                p.drawEllipse(center, r_current, r_current)

        p.setPen(QPen(ChartTheme.GRID, 1))
        p.drawLine(
            QPointF(center.x(), center.y() - radius * 1.1),
            QPointF(center.x(), center.y() + radius * 1.1),
        )
        p.drawLine(
            QPointF(center.x() - radius * 1.1, center.y()),
            QPointF(center.x() + radius * 1.1, center.y()),
        )

    def _draw_cartesian_grid(
        self, p, rect, y_max, t_start, t_end, duration, num_ticks, fmt
    ):
        (px, py, pw, ph) = rect
        p.setFont(QFont("Arial", 8))
        grid_pen = QPen(ChartTheme.GRID_FAINT, 1, Qt.PenStyle.DashLine)

        sub_color = QColor(ChartTheme.GRID_FAINT)
        sub_color.setAlpha(30)
        sub_grid_pen = QPen(sub_color, 1, Qt.PenStyle.DotLine)

        total_y_steps = num_ticks * 2
        for i in range(total_y_steps + 1):
            ratio = i / total_y_steps
            y = (py + ph) - (ratio * ph)
            val = ratio * y_max
            is_main = i % 2 == 0
            if is_main:
                p.setPen(grid_pen)
                p.drawLine(QPointF(px, y), QPointF(px + pw, y))
                p.setPen(ChartTheme.TEXT)
                txt = fmt(val)
                tw = p.fontMetrics().horizontalAdvance(txt)
                p.drawText(int(px - tw - 5), int(y + 4), txt)
            else:
                p.setPen(sub_grid_pen)
                p.drawLine(QPointF(px, y), QPointF(px + pw, y))

        target_step = duration / max(1, num_ticks)
        nice_intervals = [
            10,
            30,
            60,
            120,
            300,
            600,
            900,
            1800,
            3600,
            7200,
            14400,
            21600,
            43200,
            86400,
        ]
        step_time = nice_intervals[-1]
        for interval in nice_intervals:
            if target_step <= interval:
                step_time = interval
                break

        sub_step_time = step_time / 2
        first_tick_ts = math.ceil(t_start / sub_step_time) * sub_step_time
        current_t = first_tick_ts

        while current_t <= t_end:
            ratio = (current_t - t_start) / duration
            if 0 <= ratio <= 1.01:
                x = px + ratio * pw
                remainder = current_t % step_time
                is_main = (remainder < 0.1) or (abs(remainder - step_time) < 0.1)

                if is_main:
                    p.setPen(grid_pen)
                    p.drawLine(QPointF(x, py), QPointF(x, py + ph))
                    dt_obj = datetime.fromtimestamp(current_t)
                    dt_label = (
                        dt_obj.strftime("%H:%M:%S")
                        if step_time < 60
                        else dt_obj.strftime("%H:%M")
                    )
                    p.setPen(ChartTheme.TEXT)
                    tw = p.fontMetrics().horizontalAdvance(dt_label)
                    p.drawText(int(x - tw / 2), int(py + ph + 20), dt_label)
                else:
                    p.setPen(sub_grid_pen)
                    p.drawLine(QPointF(x, py), QPointF(x, py + ph))
            current_t += sub_step_time

        p.setPen(QPen(ChartTheme.GRID, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(int(px), int(py), int(pw), int(ph))
        p.setPen(ChartTheme.TEXT)
        title = self.tr("Distance ▲") if "km" in fmt(0) else self.tr("Confidence ▲")
        p.drawText(int(px), int(py - 10), title)

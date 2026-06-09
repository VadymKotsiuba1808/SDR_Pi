import math
from typing import Optional

import numpy as np
from PyQt6.QtCore import QPoint, QPointF, QRect, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
)

from app.core.chart_theme import ChartTheme
from app.core.constants import (
    DB_OFFSET,
    VISUAL_MAX_DB,
    VISUAL_MIN_DB,
    VISUAL_RANGE_DB,
)
from app.core.mixins import TranslatorMixin
from app.models.chart_models import CursorState
from app.models.detection_background import SpectralData
from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType
from app.utils.chart_math import ChartMath
from app.utils.convert_measurement_unit import convert_hz_to_mhz


class SpectralChartRenderer(TranslatorMixin):
    """
    Рендерер для графіків.
    Логіка: Background дає форму кривої/колір. Event дає позицію маркера.
    """

    def __init__(self):
        self.cached_heatmap = None
        self._last_bg_id = None

    def prepare_cache(self, background: Optional[SpectralData]) -> None:
        """Кешує heatmap для фону, бо це важка операція"""
        if not background or background.data_magnitude is None:
            return

        matrix = background.data_magnitude
        if isinstance(matrix, np.ndarray) and len(matrix.shape) > 1:
            self.cached_heatmap = ChartMath.create_heatmap(matrix)
        elif (
            isinstance(matrix, list) and len(matrix) > 0 and isinstance(matrix[0], list)
        ):
            self.cached_heatmap = ChartMath.create_heatmap(np.array(matrix))

    def render_spectrum(
        self,
        p: QPainter,
        rect: QRect,
        background: Optional[SpectralData],
        event: Optional[DetectionEvent] = None,
    ) -> None:

        if not background:
            p.setPen(ChartTheme.TEXT)
            p.drawText(
                rect, Qt.AlignmentFlag.AlignCenter, self.tr("Waiting for Background...")
            )
            return

        # 1. Малюємо СІТКУ
        src_type = event.type if event else SourceType.RF
        self._draw_grid(p, rect, background, src_type, mode="dbm")

        # 2. Малюємо КРИВУ СПЕКТРУ
        bg_data = background.data_magnitude
        if bg_data is not None:
            curve = bg_data

            if isinstance(bg_data, np.ndarray) and len(bg_data.shape) > 1:
                curve = np.max(bg_data, axis=0)
            elif (
                isinstance(bg_data, list)
                and len(bg_data) > 0
                and isinstance(bg_data[0], list)
            ):
                curve = np.max(np.array(bg_data), axis=0)

            # Малюємо як заповнену область
            self._draw_curve(p, rect, curve, is_fill=True)

        # 3. Малюємо МАРКЕР ПОДІЇ
        if event:
            self._draw_event_marker(p, rect, background, event)

    def render_waterfall(
        self,
        p: QPainter,
        rect: QRect,
        background: Optional[SpectralData],
        event: Optional[DetectionEvent] = None,
    ) -> None:
        if not background:
            return

        # 1. Малюємо HEATMAP
        if self.cached_heatmap:
            p.drawImage(rect, self.cached_heatmap)
        else:
            matrix = background.data_magnitude
            if matrix is None:
                return

            if isinstance(matrix, list):
                matrix = np.array(matrix, dtype=np.uint8)

            # 2. Якщо прийшов 1D масив -> робимо його 2D (1 рядок)
            if len(matrix.shape) == 1:
                matrix = np.expand_dims(matrix, axis=0)
                matrix = background.data_magnitude

                img = ChartMath.create_heatmap(matrix)
                p.drawImage(rect, img)

        # 2. Малюємо СІТКУ
        src_type = event.type if event else SourceType.RF
        self._draw_grid(p, rect, background, src_type, mode="time")

        # 3. Малюємо МАРКЕР (лінію) для події
        if event:
            self._draw_event_marker(p, rect, background, event)

    def calculate_cursor(
        self,
        pos: QPoint,
        rect: QRect,
        background: SpectralData,
        chart_type: str,
        event: Optional[DetectionEvent] = None,
    ) -> CursorState:

        check_pos = pos

        if not rect.contains(check_pos) or not background:
            return CursorState(visible=False)

        x_px = pos.x()
        rx = (x_px - rect.left()) / rect.width()

        freq_hz = (background.center_freq_hz - background.sample_rate_hz / 2) + (
            rx * background.sample_rate_hz
        )

        label_text = self.tr("{:.3f} MHz").format(convert_hz_to_mhz(freq_hz))
        highlight_pt = None

        if chart_type == "spectrum":
            data_vec = background.data_magnitude
            if isinstance(data_vec, np.ndarray) and len(data_vec.shape) > 1:
                data_vec = np.max(data_vec, axis=0)
            elif (
                isinstance(data_vec, list)
                and len(data_vec) > 0
                and isinstance(data_vec[0], list)
            ):
                data_vec = np.max(np.array(data_vec), axis=0)

            if data_vec is not None and len(data_vec) > 0:
                col_idx = int(rx * (len(data_vec) - 1))
                col_idx = max(0, min(col_idx, len(data_vec) - 1))

                val_uint8 = data_vec[col_idx]
                db_val = float(val_uint8) - DB_OFFSET

                display_db = max(min(db_val, VISUAL_MAX_DB), VISUAL_MIN_DB)
                ratio = (display_db - VISUAL_MIN_DB) / VISUAL_RANGE_DB
                y_pos = rect.bottom() - (ratio * rect.height())

                highlight_pt = QPointF(x_px, y_pos)
                label_text += self.tr(" | {:.1f} dB").format(db_val)

        elif chart_type == "waterfall":
            ry = (pos.y() - rect.top()) / rect.height()
            time_s = -background.duration_sec + (ry * background.duration_sec)
            label_text += self.tr(" | {:.2f}s").format(time_s)

        return CursorState(
            visible=True,
            pos=pos,
            text=label_text,
            show_horizontal=(chart_type == "waterfall"),
            highlight_point=highlight_pt,
        )

    def _draw_event_marker(
        self, p: QPainter, rect: QRect, bg: SpectralData, event: DetectionEvent
    ):
        """Малює вертикальну лінію та підсвітку на частоті детекції"""

        start_freq = bg.center_freq_hz - (bg.sample_rate_hz / 2)
        freq_offset = event.frequency_hz - start_freq

        # Якщо частота події виходить за межі огляду фону - не малюємо
        if freq_offset < 0 or freq_offset > bg.sample_rate_hz:
            return

        ratio_x = freq_offset / bg.sample_rate_hz
        x_px = rect.left() + (ratio_x * rect.width())

        # Малюємо лінію
        p.setPen(QPen(QColor(255, 255, 0, 180), 2, Qt.PenStyle.DashLine))  # Yellow
        p.drawLine(int(x_px), rect.top(), int(x_px), rect.bottom())

        # Малюємо трикутник зверху (маркер)
        p.setBrush(QBrush(QColor(255, 255, 0)))
        p.setPen(Qt.PenStyle.NoPen)
        triangle = QPolygonF(
            [
                QPointF(x_px, rect.top()),
                QPointF(x_px - 6, rect.top() - 8),
                QPointF(x_px + 6, rect.top() - 8),
            ]
        )
        p.drawPolygon(triangle)

        p.setPen(QColor(255, 255, 0))
        p.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        p.drawText(int(x_px) + 8, int(rect.top()) + 15, event.name)

    def _draw_curve(self, p: QPainter, rect: QRect, data: np.ndarray, is_fill: bool):
        num_points = len(data)
        if num_points < 2:
            return

        width_step = rect.width() / (num_points - 1)
        poly = QPolygonF()

        if is_fill:
            poly.append(QPointF(float(rect.left()), float(rect.bottom())))

        for i, val in enumerate(data):
            x = rect.left() + (i * width_step)
            db = float(val) - DB_OFFSET
            disp_db = max(min(db, VISUAL_MAX_DB), VISUAL_MIN_DB)
            ratio = (disp_db - VISUAL_MIN_DB) / VISUAL_RANGE_DB
            y = rect.bottom() - (ratio * rect.height())
            poly.append(QPointF(x, y))

        if is_fill:
            poly.append(QPointF(float(rect.right()), float(rect.bottom())))

            grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
            grad.setColorAt(0, ChartTheme.SPECTRUM_AVG_FILL)
            grad.setColorAt(1, ChartTheme.SPECTRUM_AVG_END)
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(poly)

        p.setPen(QPen(ChartTheme.SPECTRUM_MAX, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolyline(poly)

    def _draw_grid(
        self, p: QPainter, rect: QRect, data: SpectralData, type: SourceType, mode: str
    ):
        p.setFont(QFont("Arial", 8))
        grid_pen = QPen(ChartTheme.GRID_FAINT, 1, Qt.PenStyle.DashLine)
        text_pen = QPen(ChartTheme.TEXT)

        # (вісь X )
        if type == SourceType.RF:
            divisor, unit, dec = 1e6, self.tr("MHz"), 2
        else:
            divisor, unit, dec = 1.0, self.tr("Hz"), 0

        center = data.center_freq_hz / divisor
        bw = data.sample_rate_hz / divisor
        start_f = center - (bw / 2)
        end_f = center + (bw / 2)

        _, nice_step, _ = ChartMath.calculate_nice_axis(bw, 8)
        if nice_step <= 0:
            nice_step = 1

        first_tick = math.ceil(start_f / nice_step) * nice_step
        current = first_tick
        while current <= end_f:
            ratio = (current - start_f) / bw
            x = rect.left() + (ratio * rect.width())
            if rect.left() <= x <= rect.right() + 1:
                p.setPen(grid_pen)
                p.drawLine(int(x), rect.top(), int(x), rect.bottom())
                p.setPen(text_pen)
                lbl = f"{current:.{dec}f}" if dec > 0 else f"{int(current)}"
                tw = p.fontMetrics().horizontalAdvance(lbl)
                p.drawText(int(x - tw / 2), rect.bottom() + 20, lbl)
            current += nice_step
        p.drawText(rect.right() - 20, rect.bottom() + 35, unit)

        # === ВІСЬ Y ===
        steps_y = 6
        for i in range(steps_y):
            ratio = i / (steps_y - 1)
            y: float = 0
            label = ""

            if mode == "dbm":
                y = rect.bottom() - (rect.height() * ratio)
                val = VISUAL_MIN_DB + (ratio * VISUAL_RANGE_DB)
                label = self.tr("{:.0f} dB").format(val)

            elif mode == "time":
                y = rect.top() + (rect.height() * ratio)
                val = -data.duration_sec + (ratio * data.duration_sec)
                label = self.tr("{:.2f}s").format(val)

            p.setPen(grid_pen)
            p.drawLine(rect.left(), int(y), rect.right(), int(y))
            p.setPen(text_pen)
            p.drawText(rect.left() - 45, int(y + 4), label)

        p.setPen(QPen(ChartTheme.GRID, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

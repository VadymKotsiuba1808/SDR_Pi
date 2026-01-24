import math
import numpy as np
from typing import Optional

from PyQt6.QtGui import QPainter, QPen, QBrush, QPolygonF, QLinearGradient, QFont
from PyQt6.QtCore import QRect, Qt, QPointF

from app.core.mixins import TranslatorMixin
from app.core.constants import (
    DB_OFFSET,
    VISUAL_MIN_DB,
    VISUAL_MAX_DB,
    VISUAL_RANGE_DB,
)
from app.models.detection_event import DetectionEvent, SpectralData
from app.models.source_type import SourceType
from app.models.chart_models import CursorState
from app.core.chart_theme import ChartTheme
from app.utils.chart_math import ChartMath
from app.utils.convert_measurement_unit import convert_hz_to_mhz


class SpectralChartRenderer(TranslatorMixin):
    """Рендерер для графіків Spectrum та Waterfall (Static)."""

    def __init__(self):
        self.cached_heatmap = None
        self.cached_spectrum_max = None
        self.cached_spectrum_avg = None
        self._last_event_id = None

    def prepare_cache(self, event: DetectionEvent) -> None:
        if not event.spectral_data:
            return
        if self._last_event_id == event.id:
            return

        matrix = event.spectral_data.data_magnitude
        self.cached_heatmap = ChartMath.create_heatmap(matrix)

        self.cached_spectrum_max = np.max(matrix, axis=0)
        self.cached_spectrum_avg = np.mean(matrix, axis=0)
        self._last_event_id = event.id

    def render_spectrum(self, p: QPainter, rect: QRect, event: DetectionEvent) -> None:
        if not event.spectral_data:
            return
        # Малюємо сітку з урахуванням нових меж
        self._draw_grid(p, rect, event.spectral_data, event.type, mode="dbm")

        if self.cached_spectrum_avg is not None:
            self._draw_curve(p, rect, self.cached_spectrum_avg, is_fill=True)
        if self.cached_spectrum_max is not None:
            self._draw_curve(p, rect, self.cached_spectrum_max, is_fill=False)

    def render_waterfall(self, p: QPainter, rect: QRect, event: DetectionEvent) -> None:
        if not event.spectral_data:
            return
        if self.cached_heatmap:

            p.drawImage(rect, self.cached_heatmap)
        self._draw_grid(p, rect, event.spectral_data, event.type, mode="time")

    def calculate_cursor(
        self, pos: QPointF, rect: QRect, event: DetectionEvent, mode: str
    ) -> CursorState:
        check_pos = pos.toPoint() if hasattr(pos, "toPoint") else pos

        if not rect.contains(check_pos) or not event.spectral_data:
            return CursorState(visible=False)

        spec_data = event.spectral_data
        x_px = pos.x()

        rx = (x_px - rect.left()) / rect.width()
        freq_hz = (spec_data.center_freq_hz - spec_data.sample_rate_hz / 2) + (
            rx * spec_data.sample_rate_hz
        )

        label = (
            (convert_hz_to_mhz(freq_hz) + self.tr("MHz"))
            if event.type == SourceType.RF
            else (int(freq_hz) + self.tr("Hz"))
        )

        highlight_pt = None

        if mode == "spectrum" and self.cached_spectrum_max is not None:
            col_idx = int(rx * (len(self.cached_spectrum_max) - 1))
            col_idx = max(0, min(col_idx, len(self.cached_spectrum_max) - 1))

            val_uint8 = self.cached_spectrum_max[col_idx]
            db_val = float(val_uint8) - DB_OFFSET

            # === РОЗРАХУНОК Y (SCALING) ===
            display_db = max(min(db_val, VISUAL_MAX_DB), VISUAL_MIN_DB)

            ratio = (display_db - VISUAL_MIN_DB) / VISUAL_RANGE_DB
            y_pos = rect.bottom() - (ratio * rect.height())

            highlight_pt = QPointF(x_px, y_pos)
            label += self.tr(" | Peak: {:.1f} dB").format(db_val)

        elif mode == "waterfall":
            ry = (pos.y() - rect.top()) / rect.height()
            time_s = -spec_data.duration_sec + (ry * spec_data.duration_sec)
            label += self.tr(" | {:.2f}s").format(time_s)

        return CursorState(
            visible=True,
            pos=pos,
            text=label,
            show_horizontal=(mode == "waterfall"),
            highlight_point=highlight_pt,
        )

    def _draw_curve(self, p: QPainter, rect: QRect, data: np.ndarray, is_fill: bool):
        num_points = len(data)
        if num_points < 2:
            return
        width_step = rect.width() / (num_points - 1)
        poly = QPolygonF()

        if is_fill:
            poly.append(QPointF(float(rect.left()), float(rect.bottom())))

        for i, val_uint8 in enumerate(data):
            x = rect.left() + (i * width_step)

            # === SCALING Y  ===
            db_val = float(val_uint8) - DB_OFFSET
            display_db = max(min(db_val, VISUAL_MAX_DB), VISUAL_MIN_DB)
            ratio = (display_db - VISUAL_MIN_DB) / VISUAL_RANGE_DB

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
        else:
            p.setPen(QPen(ChartTheme.SPECTRUM_MAX_GLOW, 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(poly)
            p.setPen(QPen(ChartTheme.SPECTRUM_MAX, 1.5))
            p.drawPolyline(poly)

    def _draw_grid(
        self, p: QPainter, rect: QRect, data: SpectralData, type: str, mode: str
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

        # === ВІСЬ Y  ===
        steps_y = 6
        for i in range(steps_y):
            ratio = i / (steps_y - 1)
            y = 0
            label = ""

            if mode == "dbm":
                y = rect.bottom() - (rect.height() * ratio)
                # Лінійна інтерполяція від MIN до MAX
                val = VISUAL_MIN_DB + (ratio * VISUAL_RANGE_DB)
                label = self.tr("{:.0f} dB").format(val)

            elif mode == "time":
                y = rect.top() + (rect.height() * ratio)
                val = -data.duration_sec + (data.duration_sec * ratio)
                label = self.tr("{:.2f}s").format(val)

            p.setPen(grid_pen)
            p.drawLine(rect.left(), int(y), rect.right(), int(y))
            p.setPen(text_pen)
            p.drawText(rect.left() - 45, int(y + 4), label)

        p.setPen(QPen(ChartTheme.GRID, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

from typing import List, Set, Optional, Tuple
import math
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import QPainter, QPaintEvent, QMouseEvent
from PyQt6.QtCore import QRect, Qt, QPointF

from app.models.detection_event import DetectionEvent
from app.models.detection_background import SpectralData
from app.models.source_type import SourceType
from app.protocols import LangSettings
from app.core.chart_theme import ChartTheme
from app.models.chart_models import CursorState
from app.utils.convert_measurement_unit import convert_hz_to_mhz

from app.ui.components.chart_crosshair import QPainterCrosshair
from app.ui.components.spectral_renderer import SpectralChartRenderer
from app.ui.components.standard_chart_renderer import StandardChartRenderer


class StaticChartWidget(QWidget):
    def __init__(
        self, settings_service: LangSettings, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.settings_service = settings_service
        self.setMouseTracking(True)

        self._setup_variables()

    def _setup_variables(self) -> None:
        self.data: List[DetectionEvent] = []
        self.highlight_ids: Set[str] = set()
        self.chart_type: str = "timeline"

        self.current_background: Optional[SpectralData] = None

        self.content_rect = QRect()
        self._interactive_points: List[Tuple[QPointF, DetectionEvent]] = []

        self.crosshair = QPainterCrosshair()
        self.spectral_renderer = SpectralChartRenderer()
        self.standard_renderer = StandardChartRenderer()

    def set_data(
        self, data: List[DetectionEvent], highlight_ids: Optional[Set[str]] = None
    ) -> None:
        self.data = sorted(data, key=lambda x: x.timestamp)
        self.highlight_ids = highlight_ids or set()
        self.update()

    def set_background(self, spectral_data: Optional[SpectralData]) -> None:
        """Встановлює дані фону для відображення на графіках спектру/водоспаду."""
        self.current_background = spectral_data

        if self.chart_type in ["spectrum", "waterfall"] and self.current_background:
            self.spectral_renderer.prepare_cache(self.current_background)

        self.update()

    def set_chart_type(self, t: str) -> None:
        if self.chart_type != t:
            self.chart_type = t

            if t in ["spectrum", "waterfall"] and self.current_background:
                self.spectral_renderer.prepare_cache(self.current_background)
            self.update()

    def _get_active_event(self) -> Optional[DetectionEvent]:
        """Повертає 'активну' подію (останню або підсвічену) для відображення маркера."""
        if not self.data:
            return None
        if self.highlight_ids:
            for d in reversed(self.data):
                if d.id in self.highlight_ids:
                    return d
        return self.data[-1]

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), ChartTheme.BG)

        self._interactive_points.clear()

        margin_left = 60
        self.content_rect = QRect(
            margin_left, 40, self.width() - (margin_left + 30), self.height() - 80
        )

        if not self.data and not self.current_background:
            p.setPen(ChartTheme.TEXT)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.tr("No Data"))
            return

        # --- ЛОГІКА МАЛЮВАННЯ СПЕКТРАЛЬНИХ ГРАФІКІВ ---
        if self.chart_type == "spectrum":
            active = self._get_active_event()

            self.spectral_renderer.render_spectrum(
                p, self.content_rect, background=self.current_background, event=active
            )
            self.crosshair.draw(p, self.content_rect)

        elif self.chart_type == "waterfall":
            active = self._get_active_event()

            self.spectral_renderer.render_waterfall(
                p, self.content_rect, background=self.current_background, event=active
            )
            self.crosshair.draw(p, self.content_rect)

        # --- СТАНДАРТНІ ГРАФІКИ ---
        elif self.chart_type in ["path", "radar_snapshot"]:
            self.standard_renderer.render_polar(
                p, self.rect(), self.data, self.highlight_ids, self._interactive_points
            )

        elif self.chart_type in ["timeline", "signal"]:
            self.standard_renderer.render_cartesian(
                p,
                self.rect(),
                self.data,
                self.chart_type,
                self.highlight_ids,
                self._interactive_points,
            )

        elif self.chart_type == "bar":
            self.standard_renderer.render_bar(p, self.rect(), self.data)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()

        if self.chart_type in ["spectrum", "waterfall"]:
            if self.current_background:
                state = self.spectral_renderer.calculate_cursor(
                    pos,
                    self.content_rect,
                    background=self.current_background,
                    chart_type=self.chart_type,
                    event=self._get_active_event(),
                )
                self.crosshair.update_state(state)
            self.update()
        else:
            self.crosshair.update_state(CursorState(visible=False))
            self.update()

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

        type_suffix = self.tr("MHz") if data.type == SourceType.RF else self.tr("Hz")
        freq_val = (
            convert_hz_to_mhz(data.frequency_hz)
            if data.type == SourceType.RF
            else data.frequency_hz
        )

        template = self.tr(
            "<b>{name}</b> ({obj_class})<br>"
            "Time: {time}<br>"
            "Dist: {dist:.3f}km, Angle: {angle:.0f}°<br>"
            "FREQ: {freq:.3f}{unit}<br>"
            "Conf: {conf:.2f}<br>"
            "Type: {type}<br>"
            "ID: {id}..."
        )

        txt = template.format(
            name=data.name,
            obj_class=data.object_class,
            time=time_str,
            dist=data.distance_km,
            angle=data.angle,
            freq=freq_val,
            unit=type_suffix,
            conf=data.confidence,
            type=data.type,
            id=data.id[:8],
        )

        if data.id in self.highlight_ids:
            highlight_msg = self.tr("HIGHLIGHTED")
            txt += f"<br><b style='color:yellow'>{highlight_msg}</b>"

        QToolTip.showText(global_pos, txt, self)

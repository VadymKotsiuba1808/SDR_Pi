"""Юніт-тести для компонента StandardChartRenderer."""

from typing import List, Tuple

import pytest
from PyQt6.QtCore import QPointF, QRect
from PyQt6.QtGui import QPainter, QPixmap

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType
from app.ui.components.standard_chart_renderer import StandardChartRenderer


@pytest.fixture
def chart_renderer() -> StandardChartRenderer:
    return StandardChartRenderer()


def create_mock_events() -> List[DetectionEvent]:
    return [
        DetectionEvent(
            id="1",
            type=SourceType.RF,
            name="Drone",
            object_class="drone",
            confidence=0.9,
            timestamp="2026-05-30T12:00:00",
            distance_km=1.0,
            angle=45.0,
            frequency_hz=2.4e9,
        )
    ]


def test_render_polar(chart_renderer: StandardChartRenderer, qtbot) -> None:
    """Перевіряє рендеринг полярного графіка (Radar/Path)."""
    img = QPixmap(500, 500)
    painter = QPainter(img)
    rect = QRect(0, 0, 500, 500)
    data = create_mock_events()
    interactive: List[Tuple[QPointF, DetectionEvent]] = []

    chart_renderer.render_polar(
        painter, rect, data, highlight_ids=set(), interactive_points=interactive
    )
    painter.end()

    assert len(interactive) == 1, "One interactive point should be added"
    assert interactive[0][1].id == "1", (
        "Event ID in the interactive point should be '1'"
    )


def test_render_cartesian(chart_renderer: StandardChartRenderer, qtbot) -> None:
    """Перевіряє рендеринг декартового графіка (Timeline)."""
    img = QPixmap(500, 500)
    painter = QPainter(img)
    rect = QRect(0, 0, 500, 500)
    data = create_mock_events()
    interactive: List[Tuple[QPointF, DetectionEvent]] = []

    chart_renderer.render_cartesian(
        painter,
        rect,
        data,
        mode="timeline",
        highlight_ids=set(),
        interactive_points=interactive,
    )
    painter.end()

    assert len(interactive) == 1, "Timeline should generate an interactive point"


def test_render_bar(chart_renderer: StandardChartRenderer, qtbot) -> None:
    """Перевіряє рендеринг гістограми розподілу за класами (smoke test)."""
    img = QPixmap(500, 500)
    painter = QPainter(img)
    rect = QRect(0, 0, 500, 500)
    data = create_mock_events()

    chart_renderer.render_bar(painter, rect, data)
    painter.end()

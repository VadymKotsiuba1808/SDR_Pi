"""
Тести для компонентів рендерингу (Standard Chart Renderer).
"""

import pytest
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QPainter, QPixmap

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType
from app.ui.components.standard_chart_renderer import StandardChartRenderer


@pytest.fixture
def chart_renderer():
    return StandardChartRenderer()


def create_mock_events():
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


def test_render_polar(chart_renderer):
    """Тест малювання полярного графіка (Radar/Path)."""
    img = QPixmap(500, 500)
    painter = QPainter(img)
    rect = QRect(0, 0, 500, 500)
    data = create_mock_events()
    interactive = []

    chart_renderer.render_polar(
        painter, rect, data, highlight_ids=set(), interactive_points=interactive
    )
    painter.end()

    # Перевіряємо, що точка додана в інтерактивний список
    assert len(interactive) == 1
    assert interactive[0][1].id == "1"


def test_render_cartesian(chart_renderer):
    """Тест малювання декартового графіка (Timeline)."""
    img = QPixmap(500, 500)
    painter = QPainter(img)
    rect = QRect(0, 0, 500, 500)
    data = create_mock_events()
    interactive = []

    chart_renderer.render_cartesian(
        painter,
        rect,
        data,
        mode="timeline",
        highlight_ids=set(),
        interactive_points=interactive,
    )
    painter.end()

    assert len(interactive) == 1


def test_render_bar(chart_renderer):
    """Тест малювання стовпчастої діаграми."""
    img = QPixmap(500, 500)
    painter = QPainter(img)
    rect = QRect(0, 0, 500, 500)
    data = create_mock_events()

    chart_renderer.render_bar(painter, rect, data)
    painter.end()
    # Якщо не впало - добре

"""Тести компонента перехрестя (Crosshair)."""

import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap

from app.models.chart_models import CursorState
from app.ui.components.chart_crosshair import QPainterCrosshair


@pytest.fixture
def crosshair() -> QPainterCrosshair:
    return QPainterCrosshair()


def test_crosshair_draw_invisible(qapp, crosshair: QPainterCrosshair) -> None:
    """Перевірка малювання невидимого курсору."""
    img = QPixmap(100, 100)
    painter = QPainter(img)
    rect = QRect(0, 0, 100, 100)

    state = CursorState(visible=False)
    crosshair.update_state(state)

    assert crosshair.state.visible is False, "Crosshair should be invisible"

    crosshair.draw(painter, rect)
    painter.end()


def test_crosshair_draw_visible(qapp, crosshair: QPainterCrosshair) -> None:
    """Перевірка малювання видимого курсору."""
    img = QPixmap(100, 100)
    painter = QPainter(img)
    rect = QRect(0, 0, 100, 100)

    pos = QPoint(50, 50)
    state = CursorState(visible=True, pos=pos, text="50.0 MHz")
    crosshair.update_state(state)

    assert crosshair.state.visible is True, "Crosshair should be visible"
    assert crosshair.state.pos == pos, "Crosshair position mismatch"
    assert crosshair.state.text == "50.0 MHz", "Crosshair text mismatch"

    crosshair.draw(painter, rect)
    painter.end()

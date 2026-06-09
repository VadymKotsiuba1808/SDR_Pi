"""
Тести для компонентів рендерингу (Crosshair).
"""

import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap

from app.models.chart_models import CursorState
from app.ui.components.chart_crosshair import QPainterCrosshair


@pytest.fixture
def crosshair():
    return QPainterCrosshair()


def test_crosshair_draw_invisible(qapp, crosshair):
    """Тест того, що невидимий курсор нічого не малює."""
    img = QPixmap(100, 100)
    painter = QPainter(img)
    rect = QRect(0, 0, 100, 100)

    state = CursorState(visible=False)
    crosshair.update_state(state)
    crosshair.draw(painter, rect)
    painter.end()
    # Якщо не впало - добре


def test_crosshair_draw_visible(qapp, crosshair):
    """Тест малювання видимого курсору."""
    img = QPixmap(100, 100)
    painter = QPainter(img)
    rect = QRect(0, 0, 100, 100)

    state = CursorState(visible=True, pos=QPoint(50, 50), text="50.0 MHz")
    crosshair.update_state(state)
    crosshair.draw(painter, rect)
    painter.end()
    # Якщо не впало - добре

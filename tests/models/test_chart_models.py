"""
Тести для моделі CursorState (chart_models.py).
"""

from PyQt6.QtCore import QPoint, QPointF

from app.models.chart_models import CursorState


def test_cursor_state_defaults():
    """Тест дефолтних значень CursorState."""
    state = CursorState()
    assert state.visible is False
    assert state.pos == QPoint(0, 0)
    assert state.text == ""
    assert state.show_horizontal is False
    assert state.highlight_point is None


def test_cursor_state_custom():
    """Тест кастомних значень CursorState."""
    pos = QPoint(100, 200)
    point = QPointF(10.5, 20.5)
    state = CursorState(
        visible=True, pos=pos, text="Test", show_horizontal=True, highlight_point=point
    )

    assert state.visible is True
    assert state.pos == pos
    assert state.text == "Test"
    assert state.show_horizontal is True
    assert state.highlight_point == point

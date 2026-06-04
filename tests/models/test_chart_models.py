"""Тести для моделей графіків."""

from PyQt6.QtCore import QPoint, QPointF

from app.models.chart_models import CursorState


def test_cursor_state_defaults() -> None:
    # Act
    state = CursorState()

    # Assert
    assert state.visible is False, "Initial visibility should be False"
    assert state.pos == QPoint(0, 0), "Initial position should be (0, 0)"
    assert state.text == "", "Initial text should be empty"
    assert state.show_horizontal is False, "Horizontal line display should be disabled"
    assert state.highlight_point is None, "Highlight point should be None"


def test_cursor_state_custom() -> None:
    # Arrange
    pos = QPoint(100, 200)
    point = QPointF(10.5, 20.5)

    # Act
    state = CursorState(
        visible=True, pos=pos, text="Test", show_horizontal=True, highlight_point=point
    )

    # Assert
    assert state.visible is True, "Visibility should be True"
    assert state.pos == pos, "Position should match the passed one"
    assert state.text == "Test", "Text should match the passed one"
    assert state.show_horizontal is True, "Horizontal line display should be True"
    assert state.highlight_point == point, "Highlight point should match the passed one"

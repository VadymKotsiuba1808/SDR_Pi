"""
Тести для UI утиліт (ui_utils).
"""

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QWidget

from app.utils.ui_utils import move_dialog_down, update_element_styles


def test_update_element_styles(qtbot):
    """Тест оновлення стилів елемента."""
    widget = QWidget()
    qtbot.addWidget(widget)
    # Перевіряємо, що функція викликається без помилок
    update_element_styles(widget)


def test_move_dialog_down(qtbot):
    """Тест переміщення діалогу вниз відносно батька."""
    dialog = QWidget()
    dialog.setFixedSize(100, 50)
    qtbot.addWidget(dialog)

    parent_geo = QRect(0, 0, 500, 500)
    move_dialog_down(dialog, parent_geo, offset_y=100)

    # x = (500 - 100) // 2 = 200
    # y = 100
    assert dialog.x() == 200
    assert dialog.y() == 100

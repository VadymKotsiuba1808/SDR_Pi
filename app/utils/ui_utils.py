from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QRect

"""
UI Утиліти.
Загальні функції для маніпуляцій з віджетами.
"""


def update_element_styles(element: QWidget) -> None:
    element.style().unpolish(element)
    element.style().polish(element)
    element.update()


def move_dialog_down(dialog: QWidget, parent_geo: QRect, offset_y: int = 80) -> None:
    new_x = parent_geo.x() + (parent_geo.width() - dialog.width()) // 2
    new_y = parent_geo.y() + offset_y

    dialog.move(new_x, new_y)

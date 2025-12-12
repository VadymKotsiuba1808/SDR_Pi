"""
UI Утиліти.
Загальні функції для маніпуляцій з віджетами.
"""


def update_element_styles(element):
    element.style().unpolish(element)
    element.style().polish(element)
    element.update()


def move_dialog_down(dialog, parent_geo, offset_y=100):
    new_x = parent_geo.x() + (parent_geo.width() - dialog.width()) // 2
    new_y = parent_geo.y() + offset_y

    dialog.move(new_x, new_y)

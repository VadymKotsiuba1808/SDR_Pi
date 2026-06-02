from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QWidget


def update_element_styles(element: QWidget) -> None:
    """Примусово оновлює стилі віджета для підтримки динамічних QSS властивостей."""
    style = element.style()

    if style is not None:
        style.unpolish(element)
        style.polish(element)
        element.update()


def move_dialog_down(dialog: QWidget, parent_geo: QRect, offset_y: int = 80) -> None:
    """Центрує вікно по горизонталі та зміщує вниз відносно батьківської геометрії."""
    new_x = parent_geo.x() + (parent_geo.width() - dialog.width()) // 2
    new_y = parent_geo.y() + offset_y

    dialog.move(new_x, new_y)

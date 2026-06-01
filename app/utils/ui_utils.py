from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QWidget


def update_element_styles(element: QWidget) -> None:
    """Примусово оновлює стилі віджета.

    Ця функція необхідна для коректного перемальовування віджета після зміни його
    динамічних властивостей (dynamic properties), які використовуються в таблицях стилів (QSS).
    Вона викликає `unpolish`, потім `polish` та `update`.

    Args:
        element (QWidget): Віджет, стилі якого потрібно оновити.
    """
    style = element.style()

    if style is not None:
        style.unpolish(element)
        style.polish(element)
        element.update()


def move_dialog_down(dialog: QWidget, parent_geo: QRect, offset_y: int = 80) -> None:
    """Центрує діалогове вікно по горизонталі відносно батьківського вікна та зміщує вниз.

    Використовується для позиціювання модальних вікон так, щоб вони не перекривали
    важливі елементи у верхній частині головного вікна.

    Args:
        dialog (QWidget): Діалогове вікно, яке потрібно перемістити.
        parent_geo (QRect): Геометрія батьківського вікна.
        offset_y (int, optional): Зміщення по вертикалі від верхнього краю батьківського вікна.
            За замовчуванням 80 пікселів.
    """
    new_x = parent_geo.x() + (parent_geo.width() - dialog.width()) // 2
    new_y = parent_geo.y() + offset_y

    dialog.move(new_x, new_y)

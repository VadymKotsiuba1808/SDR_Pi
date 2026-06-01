from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF


@dataclass
class CursorState:
    """
    Клас, що представляє стан курсору на графіку.

    Використовується для передачі інформації про стан курсору між методами оновлення
    даних (`update`) та малювання (`paint`) у віджетах графіків.

    Attributes:
        visible (bool): Чи видимий курсор у даний момент.
        pos (QPoint): Координати курсору на віджеті.
        text (str): Текст підказки (tooltip), що відображається біля курсору.
        show_horizontal (bool): Чи потрібно відображати горизонтальну лінію курсору.
        highlight_point (Optional[QPointF]): Точка даних, яку потрібно виділити
            (наприклад, найближча до курсору точка на графіку).
    """

    visible: bool = False
    pos: QPoint = field(default_factory=lambda: QPoint(0, 0))
    text: str = ""
    show_horizontal: bool = False
    highlight_point: Optional[QPointF] = None

from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF


@dataclass
class CursorState:
    """
    ### Стан курсору на графіку

    Клас для передачі інформації про стан курсору між методами оновлення даних та малювання у віджетах графіків.

    - **visible**: Видимість курсору.
    - **pos**: Координати на віджеті.
    - **text**: Текст підказки (tooltip).
    - **show_horizontal**: Відображення горизонтальної лінії.
    - **highlight_point**: Точка даних для виділення.
    """

    visible: bool = False
    pos: QPoint = field(default_factory=lambda: QPoint(0, 0))
    text: str = ""
    show_horizontal: bool = False
    highlight_point: Optional[QPointF] = None

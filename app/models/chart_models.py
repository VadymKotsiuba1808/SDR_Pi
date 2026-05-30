from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF


@dataclass
class CursorState:
    """Стан курсору для передачі між update та paint."""

    visible: bool = False
    pos: QPoint = field(default_factory=lambda: QPoint(0, 0))
    text: str = ""
    show_horizontal: bool = False
    highlight_point: Optional[QPointF] = None

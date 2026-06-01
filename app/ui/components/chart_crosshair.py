import pyqtgraph as pg
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QBrush, QPainter, QPen

from app.core.chart_theme import ChartTheme
from app.models.chart_models import CursorState


class QPainterCrosshair:
    """Компонент, що відповідає виключно за малювання курсору.

    Цей клас використовує `QPainter` для малювання ліній курсору, точок підсвічування
    та спливаючих підказок (tooltips) на полотні.

    Attributes:
        pen (QPen): Перо для малювання основних ліній курсору.
        text_pen (QPen): Перо для малювання тексту.
        bg_brush (QBrush): Пензель для фону спливаючої підказки.
        state (CursorState): Поточний стан курсору (позиція, видимість тощо).
    """

    def __init__(self) -> None:
        """Ініціалізує об'єкт QPainterCrosshair налаштуваннями стилю за замовчуванням."""
        self.pen = QPen(ChartTheme.HIGHLIGHT, 1, Qt.PenStyle.DashLine)
        self.text_pen = QPen(ChartTheme.HIGHLIGHT)
        self.bg_brush = QBrush(ChartTheme.HIGHLIGHT_BG)
        self.state = CursorState()

    def update_state(self, state: CursorState) -> None:
        """Оновлює внутрішній стан курсору.

        Args:
            state (CursorState): Новий стан курсору.
        """
        self.state = state

    def draw(self, p: QPainter, bounds: QRect) -> None:
        """Малює курсор на вказаному QPainter у межах заданого прямокутника.

        Args:
            p (QPainter): Об'єкт малювальника.
            bounds (QRect): Границі області малювання.
        """
        if not self.state.visible or not bounds.contains(self.state.pos):
            return

        x = self.state.pos.x()
        y = self.state.pos.y()

        p.setPen(self.pen)
        p.drawLine(int(x), bounds.top(), int(x), bounds.bottom())

        if self.state.show_horizontal:
            p.drawLine(bounds.left(), int(y), bounds.right(), int(y))

        if self.state.highlight_point is not None:
            p.setBrush(self.pen.color())
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.state.highlight_point, 4, 4)

        if self.state.text:
            self._draw_tooltip_box(p, x, y, bounds)

    def _draw_tooltip_box(self, p: QPainter, x: float, y: float, bounds: QRect) -> None:
        """Малює рамку з текстом підказки біля позиції курсору.

        Args:
            p (QPainter): Об'єкт малювальника.
            x (float): Координата X курсору.
            y (float): Координата Y курсору.
            bounds (QRect): Границі області малювання для обчислення позиції рамки.
        """
        fm = p.fontMetrics()
        text = self.state.text
        tw = fm.horizontalAdvance(text)
        th = fm.height()

        box_x = x + 10
        box_y = y - 25
        box_w = tw + 10
        box_h = th + 4

        # Перевірка виходу за межі області малювання
        if box_x + box_w > bounds.right():
            box_x = x - box_w - 10
        if box_y < bounds.top():
            box_y = y + 10

        bg_rect = QRect(int(box_x), int(box_y), int(box_w), int(box_h))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.bg_brush)
        p.drawRect(bg_rect)

        p.setPen(self.text_pen)

        p.drawText(int(bg_rect.left() + 5), int(bg_rect.bottom() - 4), text)


class PyGraphCrosshair:
    """Курсор спеціально для інтеграції з pyqtgraph.

    Цей клас керує об'єктами `pg.InfiniteLine` та `pg.TextItem` для відображення
    курсору на графіках `DynamicChartWidget`.

    Attributes:
        v_line (pg.InfiniteLine): Вертикальна лінія курсору.
        h_line (pg.InfiniteLine): Горизонтальна лінія курсору.
        label (pg.TextItem): Текстова мітка з координатами або іншою інформацією.
    """

    def __init__(self, plot_item: pg.PlotItem) -> None:
        """Ініціалізує курсор та додає його елементи до графіка.

        Args:
            plot_item (pg.PlotItem): Елемент графіка pyqtgraph, до якого додається курсор.
        """
        self._plot_item = plot_item

        pen = pg.mkPen(
            ChartTheme.DYN_CROSSHAIR_PEN, width=1, style=Qt.PenStyle.DashLine
        )
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pen)

        bg_color = ChartTheme.HIGHLIGHT_BG
        self.label = pg.TextItem(
            anchor=(0, 1),
            color=ChartTheme.DYN_CROSSHAIR_PEN,
            fill=pg.mkBrush(
                bg_color.red(), bg_color.green(), bg_color.blue(), bg_color.alpha()
            ),
        )

        self._plot_item.addItem(self.v_line, ignoreBounds=True)
        self._plot_item.addItem(self.h_line, ignoreBounds=True)
        self._plot_item.addItem(self.label, ignoreBounds=True)
        self.hide()

    def update_position(self, x: float, y: float, text: str) -> None:
        """Оновлює позицію ліній та текст мітки курсору.

        Args:
            x (float): Координата X на графіку.
            y (float): Координата Y на графіку.
            text (str): Текст, що відображатиметься у мітці.
        """
        self.v_line.setPos(x)
        self.h_line.setPos(y)
        self.label.setText(text)
        self.label.setPos(x, y)

        if not self.v_line.isVisible():
            self.show()

    def show(self) -> None:
        """Робить курсор видимим."""
        self.v_line.show()
        self.h_line.show()
        self.label.show()

    def hide(self) -> None:
        """Приховує курсор."""
        self.v_line.hide()
        self.h_line.hide()
        self.label.hide()

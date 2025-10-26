from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QWidget,
    QApplication,
    QVBoxLayout,
    QDialog,
    QMainWindow,
)
from PyQt6.QtGui import QPainter, QGuiApplication
from PyQt6.QtCore import Qt, QRectF


def make_scalable(base_class):
    """
    Фабрика класів: створює клас-обгортку, який масштабує
    внутрішній віджет (з фіксованим розміром)
    для заповнення всього доступного простору вікна.

    Працює з QMainWindow, QDialog, QWidget.
    """

    class ScalableWindow(base_class):
        def __init__(self, widget_to_scale):
            super().__init__()

            self.ui_widget = widget_to_scale
            # Зберігаємо базові розміри
            self.base_width = self.ui_widget.width()
            self.base_height = self.ui_widget.height()

            # Встановлюємо сцену з розмірами нашого віджета
            self.scene = QGraphicsScene(0, 0, self.base_width, self.base_height)
            self.proxy = self.scene.addWidget(self.ui_widget)

            self.view = QGraphicsView(self.scene)
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            # Вимикаємо смуги прокрутки, оскільки ми масштабуємо
            self.view.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            # Встановлюємо прозорий фон для QGraphicsView
            self.view.setStyleSheet("background: transparent")

            # Якщо 'base_class' є QDialog, ми повинні з'єднати сигнали.
            if base_class is QDialog:
                self.setWindowFlags(
                    Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
                )

                # З'єднуємо сигнали "accepted" та "rejected"
                # ВНУТРІШНЬОГО віджета (widget_to_scale)
                # зі слотами "accept" та "reject"
                # ЗОВНІШНЬОГО вікна (self).
                if isinstance(widget_to_scale, QDialog):
                    widget_to_scale.accepted.connect(self.accept)
                    widget_to_scale.rejected.connect(self.reject)

            # Розміщуємо QGraphicsView всередині обгортки
            if hasattr(self, "setCentralWidget"):
                # Шлях для QMainWindow
                self.setCentralWidget(self.view)
            else:
                # Шлях для QDialog або QWidget
                if self.layout() is None:
                    lay = QVBoxLayout(self)
                    self.setLayout(lay)

                # Прибираємо відступи, щоб view заповнював усе вікно
                self.layout().setContentsMargins(0, 0, 0, 0)
                self.layout().addWidget(self.view)

            # Встановлюємо початковий розмір обгортки
            self.resize(self.base_width, self.base_height)

        def resizeEvent(self, event):
            # Перехоплюємо подію зміни розміру вікна
            super().resizeEvent(event)
            self.fitInView()

        def fitInView(self):
            # Ця функція тепер масштабує вміст до поточного розміру вікна

            view_rect = self.view.viewport().rect()
            if view_rect.isEmpty():
                return

            scene_rect = self.scene.sceneRect()

            # Використовуємо вбудовану функцію Qt для ідеального масштабування
            self.view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

        def exec(self):
            # Якщо викликається exec() (для QDialog),
            # ми спочатку показуємо вікно на весь екран.
            self.showFullScreen()
            return super().exec()

        def showEvent(self, event):
            # Також викликаємо fitInView при першому показі
            super().showEvent(event)
            self.fitInView()

        # --- ЗАМІНА: АВТОМАТИЧНА ПЕРЕАДРЕСАЦІЯ ---
        def __getattr__(self, name):
            """
            Цей магічний метод автоматично викликається,
            якщо атрибут 'name' не знайдено у ScalableWindow.
            Він перенаправляє запит до внутрішнього ui_widget.

            Це дозволяє викликати 'scalable_dialog.get_settings()'
            безпосередньо.
            """
            try:
                # Намагаємося отримати атрибут (метод або властивість)
                # у внутрішнього віджета
                return getattr(self.ui_widget, name)
            except AttributeError:
                # Якщо його немає і там, викликаємо стандартну помилку
                raise AttributeError(
                    f"'{type(self).__name__}' object (and its wrapped 'ui_widget') "
                    f"has no attribute '{name}'"
                )

        # --- КІНЕЦЬ ЗАМІНИ ---

    return ScalableWindow


def make_window_stretched(widget):

    widget.setSizeGripEnabled(True)
    widget.setModal(True)

    widget.setWindowFlags(Qt.WindowType.Window)
    # або Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint якщо хочеш без рамок
    screen = QGuiApplication.primaryScreen().geometry()
    widget.setGeometry(screen)

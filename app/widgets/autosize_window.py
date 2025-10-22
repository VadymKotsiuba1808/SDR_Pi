from PyQt6.QtWidgets import (
 QGraphicsScene, QGraphicsView, QWidget, QApplication, QVBoxLayout
)
from PyQt6.QtGui import QPainter, QGuiApplication
from PyQt6.QtCore import Qt


def make_scalable(base_class):
    """
    Фабрика класів: створює універсальний клас, який можна наслідувати
    від будь-якого Qt-класу (QMainWindow, QDialog, QWidget і т.д.)
    """
    class ScalableWindow(base_class):
        def __init__(self, widget):
            super().__init__()

            self.ui_widget = widget
            self.base_width = self.ui_widget.width()
            self.base_height = self.ui_widget.height()

            self.scene = QGraphicsScene()
            self.scene.addWidget(self.ui_widget)

            self.view = QGraphicsView(self.scene)
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            # якщо клас підтримує setCentralWidget (як QMainWindow)
            if hasattr(self, "setCentralWidget"):
                self.setCentralWidget(self.view)
            else:
                # гарантуємо, що є layout
                if self.layout() is None:
                    lay = QVBoxLayout(self)
                    self.setLayout(lay)
                self.layout().addWidget(self.view)

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.fitInView()

        def fitInView(self):
            view_rect = self.view.viewport().rect()
            if view_rect.isEmpty():
                return

            primary_screen = QGuiApplication.primaryScreen()
            screen_geometry = primary_screen.geometry()
            width = screen_geometry.width() - 10
            height = screen_geometry.height() - 10

            scale_x = width / self.base_width
            scale_y = height / self.base_height
            scale = min(scale_x, scale_y)

            self.view.resetTransform()
            self.view.scale(scale, scale)

    return ScalableWindow

def make_window_stretched(widget):
    
    widget.setSizeGripEnabled(True)
    widget.setModal(True)

    widget.setWindowFlags(Qt.WindowType.Window)
        # або Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint якщо хочеш без рамок
    screen = QGuiApplication.primaryScreen().geometry()
    widget.setGeometry(screen)


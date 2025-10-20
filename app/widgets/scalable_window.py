
from PyQt6.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsView
from PyQt6.QtGui import QPainter, QGuiApplication

class ScalableWindow(QMainWindow):
    """
    Універсальна обгортка, яка робить будь-який віджет масштабованим
    і відображає його в повноекранному режимі.
    """
    def __init__(self, content_widget):
        super().__init__()
        self.setWindowTitle("Scalable Application")

        # 1. Приймаємо готовий віджет
        self.ui_widget = content_widget
        
        # Зберігаємо оригінальний розмір переданого віджета
        self.base_width = self.ui_widget.width()
        self.base_height = self.ui_widget.height()

        # 2. Створюємо сцену і додаємо на неї наш віджет
        self.scene = QGraphicsScene()
        self.scene.addWidget(self.ui_widget)
        
        # 3. Створюємо QGraphicsView для відображення сцени
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 4. Встановлюємо view як центральний віджет
        self.setCentralWidget(self.view)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView()

    def fitInView(self):
        view_rect = self.view.viewport().rect()
        if view_rect.isEmpty():
            return
            
        primary_screen = QGuiApplication.primaryScreen()
        screen_geometry = primary_screen.geometry()
        width=screen_geometry.width()-10
        height=screen_geometry.height()-10
        scale_x = width / self.base_width
        scale_y =height / self.base_height
        
        scale = min(scale_x,scale_y)
        
        self.view.resetTransform()
        self.view.scale(scale, scale)
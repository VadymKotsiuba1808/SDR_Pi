import re
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import (
    QAction,
    QGuiApplication,
    QMouseEvent,
    QPalette,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsScene,
    QGraphicsView,
    QMainWindow,
    QMenu,
    QWidget,
)

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def make_window_stretched(widget: QDialog) -> None:
    """Розтягує вікно на весь первинний екран."""
    widget.setSizeGripEnabled(True)
    widget.setModal(True)
    widget.setWindowFlags(Qt.WindowType.Window)

    pr_screen = QGuiApplication.primaryScreen()
    if pr_screen is not None:
        screen = pr_screen.geometry()
        widget.setGeometry(screen)


class ScaledComboBox(QComboBox):
    """Спеціалізований QComboBox для масштабованого інтерфейсу.

    Цей віджет замінює стандартний випадаючий список на кастомне QMenu, щоб
    уникнути проблем з відображенням тексту та елементів при масштабуванні
    через QGraphicsView. Він дзеркалює стан прихованого оригінального комбобокса.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        style_data: Optional[dict] = None,
        old_combo_to_forward_to: Optional[QComboBox] = None,
    ) -> None:
        """Ініціалізація ScaledComboBox."""
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.hidden_combo = old_combo_to_forward_to

        if style_data:
            self._menu_style_data = style_data
        else:
            self._menu_style_data = {
                "background": "#FFFFFF",
                "color": "#000000",
                "selection-background": "#0078D7",
                "selection-color": "#FFFFFF",
                "border": "1px solid #888888",
            }

        logger.debug(f"[ScaledComboBox] Initialized for {self.objectName()}")

    def showPopup(self) -> None:
        """Показ кастомного меню замість стандартного попапа."""
        self.create_custom_menu()

    def mousePressEvent(self, e: Optional[QMouseEvent]) -> None:
        """Обробка натискання миші для виклику кастомного меню."""
        if e and e.button() == Qt.MouseButton.LeftButton:
            self.create_custom_menu()
        else:
            super().mousePressEvent(e)

    def create_custom_menu(self) -> None:
        """Створює та відображає стилізоване QMenu з елементами комбобокса."""
        menu = QMenu(self)
        menu.setFont(self.font())

        data = self._menu_style_data
        font_size = self.font().pointSize()
        if font_size <= 0:
            font_size = 28

        menu_stylesheet = f"""
            QMenu {{
                font-size: {font_size}px;
                background-color: {data["background"]};
                color: {data["color"]};
                border: {data["border"]};
            }}
            QMenu::item {{ padding: 8px 20px 8px 20px; }}
            QMenu::item:selected {{
                background-color: {data["selection-background"]};
                color: {data["selection-color"]};
            }}
        """
        menu.setStyleSheet(menu_stylesheet)

        for i in range(self.count()):
            action = QAction(self.itemIcon(i), self.itemText(i), self)
            if i == self.currentIndex():
                action.setCheckable(True)
                action.setChecked(True)

            action.triggered.connect(
                lambda checked=False, index=i: self.set_selection(index)
            )
            menu.addAction(action)

        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        menu.exec(global_pos)

    @pyqtSlot(int)
    def set_selection(self, index: int) -> None:
        """Встановлює вибраний елемент та передає подію прихованому комбобоксу."""
        self.blockSignals(True)
        self.setCurrentIndex(index)
        self.blockSignals(False)

        if self.hidden_combo:
            logger.debug(
                f"[ScaledComboBox] Forwarding index {index} to hidden combobox"
            )
            self.hidden_combo.setCurrentIndex(index)


def enable_auto_scaling(
    window: QMainWindow, base_width: int = 1920, base_height: int = 1080
) -> None:
    """Вмикає автоматичне масштабування для головного вікна."""
    original_widget = window.centralWidget()
    if not original_widget:
        logger.error("[AutoScaler] Error: No centralWidget found.")
        return

    logger.debug("[AutoScaler] Starting auto-scaling...")

    all_comboboxes = list(original_widget.findChildren(QComboBox))
    logger.debug(
        f"[AutoScaler] Found {len(all_comboboxes)} QComboBoxes for replacement."
    )

    for old_combo in all_comboboxes:
        if isinstance(old_combo, ScaledComboBox):
            continue

        logger.debug(f"[AutoScaler] Replacing {old_combo.objectName()}...")

        # Зчитуємо стилі для передачі в новий комбобокс
        combo_view = old_combo.view()
        if combo_view is None:
            logger.error(
                f"[AutoScaler] Error: Could not get view for {old_combo.objectName()}"
            )
            continue

        view_palette = combo_view.palette()
        style_data = {
            "background": view_palette.color(QPalette.ColorRole.Base).name(),
            "color": view_palette.color(QPalette.ColorRole.Text).name(),
            "selection-background": view_palette.color(
                QPalette.ColorRole.Highlight
            ).name(),
            "selection-color": view_palette.color(
                QPalette.ColorRole.HighlightedText
            ).name(),
        }

        # Спроба витягти стиль рамки з stylesheet
        border_style = "1px solid black"
        match = re.search(
            r"QComboBox\s*\{[^\}]*border\s*:\s*([^;\}]+)",
            old_combo.styleSheet(),
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            match = re.search(
                r"border\s*:\s*([^;\}]+)", old_combo.styleSheet(), re.IGNORECASE
            )
        if match:
            border_style = match.group(1).strip()
        style_data["border"] = border_style

        logger.debug(f"[AutoScaler]   -> Styles read: {style_data}")

        # Створюємо ScaledComboBox, який буде проксі-віджетом для старого
        parent = old_combo.parentWidget()
        new_combo = ScaledComboBox(
            parent, style_data, old_combo_to_forward_to=old_combo
        )

        # Копіюємо стан та геометрію
        new_combo.addItems([old_combo.itemText(i) for i in range(old_combo.count())])
        new_combo.setCurrentIndex(old_combo.currentIndex())
        new_combo.setObjectName(old_combo.objectName())
        new_combo.setStyleSheet(old_combo.styleSheet())
        new_combo.setFont(old_combo.font())
        new_combo.setGeometry(old_combo.geometry())

        # Оновлюємо посилання в об'єкті UI, якщо він існує
        attr_name = old_combo.objectName()
        window_ui = getattr(window, "ui", None)

        if window_ui is not None and hasattr(window_ui, attr_name):
            setattr(window_ui, attr_name, new_combo)
            logger.debug(f"[AutoScaler]   -> Updated attribute 'window.ui.{attr_name}'")

        # Ховаємо старий віджет, але не видаляємо, бо він потрібен як джерело сигналів
        old_combo.setVisible(False)
        new_combo.setVisible(True)

    # Налаштування сцени для масштабування
    scene = QGraphicsScene(0, 0, base_width, base_height)
    view = QGraphicsView(scene)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setStyleSheet("background: black; border: none;")

    original_widget.setParent(None)
    scene.addWidget(original_widget)
    window.setCentralWidget(view)

    pr_screen = QGuiApplication.primaryScreen()
    if pr_screen is None:
        logger.error("[AutoScaler] Error: Could not get primaryScreen.")
        return

    screen_rect = pr_screen.geometry()
    scale_x = screen_rect.width() / base_width
    scale_y = screen_rect.height() / base_height
    scale = min(scale_x, scale_y)

    logger.debug(
        f"[AutoScaler] Screen: {screen_rect.width()}x{screen_rect.height()}. Scale: {scale}"
    )

    view.scale(scale, scale)
    view.centerOn(base_width / 2, base_height / 2)

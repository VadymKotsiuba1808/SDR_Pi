"""
Адаптивне вікно.
Базовий клас або функції для віджетів, що реалізує логіку автоматичного масштабування та підлаштування розмірів елементів під роздільну здатність екрану.
"""

import re

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import (
    QAction,
    QGuiApplication,
    QMouseEvent,
    QPalette,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QGraphicsScene,
    QGraphicsView,
    QMainWindow,
    QMenu,
)


def make_window_stretched(widget):

    widget.setSizeGripEnabled(True)
    widget.setModal(True)

    widget.setWindowFlags(Qt.WindowType.Window)

    pr_screen = QGuiApplication.primaryScreen()
    if pr_screen is not None:
        screen = pr_screen.geometry()
        widget.setGeometry(screen)


class ScaledComboBox(QComboBox):
    """
    Цей QComboBox приймає словник стилів І "старий" комбобокс,
    сигнали якого він буде "дзеркалити".
    """

    # (ОНОВЛЕНИЙ __init__)
    def __init__(self, parent=None, style_data=None, old_combo_to_forward_to=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Зберігаємо прихований комбобокс
        self.hidden_combo = old_combo_to_forward_to

        # Зберігаємо передані стилі
        if style_data:
            self._menu_style_data = style_data
        else:
            # Аварійний варіант
            self._menu_style_data = {
                "background": "#FFFFFF",
                "color": "#000000",
                "selection-background": "#0078D7",
                "selection-color": "#FFFFFF",
                "border": "1px solid #888888",
            }

        print(f"[ScaledComboBox] Ініціалізовано для {self.objectName()}")

    def showPopup(self):
        self.create_custom_menu()

    def mousePressEvent(self, e: QMouseEvent | None) -> None:
        event = e
        if event and event.button() == Qt.MouseButton.LeftButton:
            self.create_custom_menu()
        else:
            super().mousePressEvent(event)

    def create_custom_menu(self):
        menu = QMenu(self)
        menu.setFont(self.font())

        data = self._menu_style_data
        font_size = self.font().pointSize()
        if font_size <= 0:
            font_size = 28  # Аварійний варіант

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

    # (ОНОВЛЕНИЙ set_selection)
    @pyqtSlot(int)
    def set_selection(self, index):
        # 1. Встановлюємо індекс для себе (це оновить UI)
        # (блокуємо сигнали, щоб не було подвійного виклику)
        self.blockSignals(True)
        self.setCurrentIndex(index)
        self.blockSignals(False)

        # 2. (ВАЖЛИВО) Встановлюємо індекс для прихованого 'old_combo',
        #    щоб ВІН випромінив сигнал до вашого обробника
        if self.hidden_combo:
            print(
                f"[ScaledComboBox] Передача індексу {index} до прихованого комбобокса"
            )
            self.hidden_combo.setCurrentIndex(index)


def enable_auto_scaling(
    window: QMainWindow, base_width: int = 1920, base_height: int = 1080
):

    original_widget = window.centralWidget()
    if not original_widget:
        print("[AutoScaler] Помилка: Немає centralWidget.")
        return

    print("[AutoScaler] Запуск масштабування...")

    all_comboboxes = list(original_widget.findChildren(QComboBox))
    print(f"[AutoScaler] Знайдено {len(all_comboboxes)} QComboBox для заміни.")

    for old_combo in all_comboboxes:
        if isinstance(old_combo, ScaledComboBox):
            continue

        print(f"[AutoScaler] Замінюю {old_combo.objectName()}...")

        # 1. Зчитуємо стилі
        combo_view = old_combo.view()
        if combo_view is None:
            print(
                f"[AutoScaler] Помилка: Не вдалося отримати view для {old_combo.objectName()}"
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

        print(f"[AutoScaler]   -> Зчитані стилі: {style_data}")

        # 2. Створюємо new_combo, ПЕРЕДАЮЧИ old_combo
        parent = old_combo.parentWidget()
        new_combo = ScaledComboBox(
            parent, style_data, old_combo_to_forward_to=old_combo
        )

        # 3. Копіюємо вміст та властивості
        new_combo.addItems([old_combo.itemText(i) for i in range(old_combo.count())])
        new_combo.setCurrentIndex(old_combo.currentIndex())
        new_combo.setObjectName(old_combo.objectName())
        new_combo.setStyleSheet(old_combo.styleSheet())
        new_combo.setFont(old_combo.font())
        new_combo.setGeometry(old_combo.geometry())

        # 4. Оновлюємо атрибут на 'window.ui'
        attr_name = old_combo.objectName()
        window_ui = getattr(window, "ui", None)

        if window_ui is not None and hasattr(window_ui, attr_name):
            setattr(window_ui, attr_name, new_combo)
            print(f"[AutoScaler]   -> Оновлено атрибут 'window.ui.{attr_name}'")

        # 5. (ВАЖЛИВО) Ховаємо старий, але НЕ видаляємо його
        old_combo.setVisible(False)
        # old_combo.deleteLater() # <--- НЕ ВИДАЛЯЄМО

        new_combo.setVisible(True)

    # --- (Решта функції без змін) ---

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
        print("[AutoScaler] Помилка: Не вдалося отримати primaryScreen.")
        return

    screen_rect = pr_screen.geometry()
    scale_x = screen_rect.width() / base_width
    scale_y = screen_rect.height() / base_height
    scale = min(scale_x, scale_y)

    print(
        f"[AutoScaler] Екран: {screen_rect.width()}x{screen_rect.height()}. Масштаб: {scale}"
    )

    view.scale(scale, scale)
    view.centerOn(base_width / 2, base_height / 2)

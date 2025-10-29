import re
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QWidget,
    QApplication,
    QVBoxLayout,
    QDialog,
    QMainWindow,
    QComboBox,
    QMenu,
)
from PyQt6.QtGui import QPainter, QGuiApplication, QResizeEvent, QAction, QPalette
from PyQt6.QtCore import Qt, QRectF, QSize, pyqtSlot
import types


def make_scalable(base_class):
    """
    Фабрика класів: створює клас-обгортку, який масштабує
    внутрішній віджет. (QGraphicsView - це правильний підхід)
    """

    class ScalableWindow(base_class):
        def __init__(self, main_window_instance, widget_to_scale):
            super().__init__()

            # 1. Зберігаємо обидва віджети
            self.main_window = main_window_instance
            self.ui_widget = widget_to_scale  # Це window.centralwidget

            # 2. Визначаємо коректний базовий розмір
            # (беремо з minimumSize, який ви встановили в .ui)
            intended_size = self.main_window.minimumSize()
            self.base_width = intended_size.width()
            self.base_height = intended_size.height()

            # Аварійний варіант, якщо розміри не зчиталися
            if self.base_width <= 0:
                print("[Scalable] Аварійне встановлення розміру 1920x1080.")
                self.base_width = 1920
                self.base_height = 1080

            print(
                f"[Scalable] ФІНАЛЬНИЙ РОЗМІР СЦЕНИ: {self.base_width}x{self.base_height}"
            )

            # 3. Створюємо сцену з коректними розмірами
            self.scene = QGraphicsScene(0, 0, self.base_width, self.base_height)

            # --- ВИРІШЕННЯ ПОМИЛКИ "cannot embed widget" ---
            # "Звільняємо" centralwidget від MainWindow,
            # щоб QGraphicsScene могла його "всиновити".
            print("[Scalable] Звільнення centralwidget (setParent(None)).")
            self.ui_widget.setParent(None)
            # --- КІНЕЦЬ ВИРІШЕННЯ ---

            # 5. Додаємо centralwidget на сцену
            print("[Scalable] Додавання centralwidget до QGraphicsScene.")
            self.proxy = self.scene.addWidget(self.ui_widget)

            # --- ВИРІШЕННЯ ПРОБЛЕМИ QCOMBOBOX ---
            all_comboboxes = self.ui_widget.findChildren(QComboBox)
            print(f"[Scalable] Знайдено {len(all_comboboxes)} QComboBox.")
            for combo in all_comboboxes:
                print(f"[Scalable] Застосовую фікс SubWindow до {combo.objectName()}")
                combo.view().setWindowFlags(Qt.WindowType.SubWindow)
            # --- КІНЕЦЬ ВИРІШЕННЯ ---

            # 7. Налаштовуємо QGraphicsView
            self.view = QGraphicsView(self.scene)
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            self.view.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.view.setStyleSheet("background: transparent")

            # 8. Обробка QDialog (якщо це діалог)
            if base_class is QDialog:
                self.setWindowFlags(
                    Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
                )
            if isinstance(self.main_window, QDialog):
                self.main_window.accepted.connect(self.accept)
                self.main_window.rejected.connect(self.reject)

            # 9. Розміщуємо QGraphicsView всередині обгортки
            if hasattr(self, "setCentralWidget"):
                self.setCentralWidget(self.view)
            else:
                if self.layout() is None:
                    lay = QVBoxLayout(self)
                    self.setLayout(lay)
                self.layout().setContentsMargins(0, 0, 0, 0)
                self.layout().addWidget(self.view)

            self.resize(self.base_width, self.base_height)

        # --- Методи для масштабування ---

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.fitInView()

        def fitInView(self):
            # Ця функція масштабує сцену (1920x1080)
            # до розміру QGraphicsView (1536x864)
            view_rect = self.view.viewport().rect()
            if view_rect.isEmpty():
                return
            scene_rect = self.scene.sceneRect()
            self.view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

        def exec(self):
            self.showFullScreen()
            return super().exec()

        def showEvent(self, event):
            super().showEvent(event)
            # Перший запуск масштабування при показі
            self.fitInView()

        # --- Метод для переадресації викликів ---
        def __getattr__(self, name):
            try:
                return getattr(self.main_window, name)
            except AttributeError:
                try:
                    return getattr(self.ui_widget, name)
                except AttributeError:
                    raise AttributeError(
                        f"'{type(self).__name__}' object (and its wrapped 'main_window'/'ui_widget') "
                        f"has no attribute '{name}'"
                    )

    return ScalableWindow


def make_window_stretched(widget):

    widget.setSizeGripEnabled(True)
    widget.setModal(True)

    widget.setWindowFlags(Qt.WindowType.Window)
    # або Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint якщо хочеш без рамок
    screen = QGuiApplication.primaryScreen().geometry()
    widget.setGeometry(screen)


def setup_auto_scaling(
    window: QMainWindow, base_width: int = 1920, base_height: int = 1080
):
    print("[AutoScaling] --- Початок налаштування ---")
    content_widget = window.centralwidget
    print(f"[AutoScaling] centralwidget: {content_widget}")

    if not content_widget:
        print("[AutoScaling] ❌ Відсутній centralwidget!")
        return

    print(f"[AutoScaling] Вікно: {window.objectName() or '<без імені>'}")
    print(f"[AutoScaling] Базовий розмір: {base_width}x{base_height}")

    window._base_size = QSize(base_width, base_height)

    window.setStyleSheet(
        f"QMainWindow#{window.objectName()} {{ background-color: black; }}"
    )
    print("[AutoScaling] Застосовано чорний фон до QMainWindow")

    def new_resizeEvent(self, event: QResizeEvent):
        print(
            f"[AutoScaling] resizeEvent → новий розмір: {event.size().width()}x{event.size().height()}"
        )

        window_size = event.size()
        new_size = self._base_size.scaled(
            window_size, Qt.AspectRatioMode.KeepAspectRatio
        )

        x = (window_size.width() - new_size.width()) / 2
        y = (window_size.height() - new_size.height()) / 2

        content_widget.setGeometry(int(x), int(y), new_size.width(), new_size.height())
        print(
            f"[AutoScaling] → centralwidget: pos=({int(x)}, {int(y)}), size={new_size.width()}x{new_size.height()}"
        )

    window.resizeEvent = types.MethodType(new_resizeEvent, window)
    print("[AutoScaling] Перевизначено resizeEvent")

    original_showEvent = window.showEvent

    def new_showEvent(self, event):
        print("[AutoScaling] showEvent → виклик початкового масштабування")
        original_showEvent(event)
        self.resizeEvent(QResizeEvent(self.size(), self.size()))

    window.showEvent = types.MethodType(new_showEvent, window)
    print("[AutoScaling] Перевизначено showEvent")

    print("[AutoScaling] --- Налаштування завершено ---\n")


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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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
                background-color: {data['background']};
                color: {data['color']};
                border: {data['border']};
            }}
            QMenu::item {{ padding: 8px 20px 8px 20px; }}
            QMenu::item:selected {{
                background-color: {data['selection-background']};
                color: {data['selection-color']};
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


# ---------------------------------------------------------------------
# Крок 2: enable_auto_scaling тепер передає old_combo
# ---------------------------------------------------------------------
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
        view_palette = old_combo.view().palette()
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
        if hasattr(window.ui, attr_name):
            setattr(window.ui, attr_name, new_combo)
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

    screen_rect = QGuiApplication.primaryScreen().geometry()
    scale_x = screen_rect.width() / base_width
    scale_y = screen_rect.height() / base_height
    scale = min(scale_x, scale_y)

    print(
        f"[AutoScaler] Екран: {screen_rect.width()}x{screen_rect.height()}. Масштаб: {scale}"
    )

    view.scale(scale, scale)
    view.centerOn(base_width / 2, base_height / 2)

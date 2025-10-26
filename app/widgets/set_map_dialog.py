import sys

# Додаємо QDialog
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6 import uic


# Змінюємо QMainWindow на QDialog
class SetMapDialog(QDialog):

    # Сигнал settings_saved БІЛЬШЕ НЕ ПОТРІБЕН

    def __init__(self, settings, add_sizes_map_k=[1, 1], parent=None):
        super().__init__(parent)
        print("[Init] Ініціалізація SetMapDialog...")

        # Зберігаємо цільовий радіус радару
        self.settings_service = settings
        self.add_sizes_map_k = add_sizes_map_k

        # Завантажуємо новий .ui файл
        uic.loadUi("app/ui/set_map_dialog.ui", self)
        print("[Init] UI завантажено")

        # Внутрішні змінні стану
        self.original_pixmap = None
        self.image_path = ""
        self.current_scale = 1.0
        self.current_offset = QPoint()
        self.is_centering_mode = False
        circle_radius = self.centerCircleLabel.width() / 2
        self.center_point = QPoint()

        self.screen_center = QPoint(
            int(self.centerCircleLabel.x() + circle_radius),
            int(self.centerCircleLabel.y() + circle_radius),
        )
        print(
            f"[Init] Розмір екрану карти: {self.mapDisplayLabel.width()}x{self.mapDisplayLabel.height()}"
        )
        print(f"[Init] Центр екрана карти: {self.screen_center}")

        self.connect_signals()
        print("[Init] Сигнали підключено")

        self.mapDisplayLabel.installEventFilter(self)
        self.centerCircleLabel.installEventFilter(self)
        self.centerPointIconLabel.installEventFilter(self)

        # Це буде словник, який ми повернемо
        self.result_settings = {}
        print("[Init] Ініціалізацію завершено\n")

    def connect_signals(self):
        self.selectImageButton.clicked.connect(self.on_select_image)
        self.setCenterButton.clicked.connect(self.on_set_center)
        self.zoomInButton.clicked.connect(self.on_zoom_in)
        self.zoomOutButton.clicked.connect(self.on_zoom_out)
        self.scaleSpinBox.valueChanged.connect(self.on_scale_changed)

        # Підключаємо кнопки до вбудованих слотів QDialog
        # (Хоча це вже є в .ui, але так надійніше)
        self.saveButton.clicked.connect(self.save)
        self.cancelButton.clicked.connect(self.cancel)

    # --- Обробники подій ---

    def on_select_image(self):
        print("[on_select_image] Відкривається діалог вибору зображення...")
        file_path, _ = QFileDialog.getOpenFileName(
            None,  # Використовуємо None для уникнення проблем з модальністю
            "Виберіть зображення карти",
            "",
            "Зображення (*.png *.jpg *.bmp *.jpeg)",
        )

        if not file_path:
            print("[on_select_image] Файл не вибрано")
            return

        print(f"[on_select_image] Обрано файл: {file_path}")
        self.image_path = file_path
        self.original_pixmap = QPixmap(self.image_path)

        if self.original_pixmap.isNull():
            print("[on_select_image] ПОМИЛКА: не вдалося завантажити зображення")
            QMessageBox.warning(
                None, "Помилка", f"Не вдалося завантажити зображення: {file_path}"
            )
            self.original_pixmap = None
            self.image_path = ""
            return

        print(
            f"[on_select_image] Зображення завантажено, розмір: {self.original_pixmap.width()}x{self.original_pixmap.height()}"
        )
        self.center_point = QPoint(self.original_pixmap.rect().center())
        print(f"[on_select_image] Початковий центр зображення: {self.center_point}")
        self.scaleSpinBox.setValue(100)
        self.centerPointIconLabel.setVisible(False)
        self.update_map_display()

    def on_set_center(self):
        print("[on_set_center] Активовано режим вибору центру")
        if not self.original_pixmap:
            QMessageBox.warning(None, "Увага", "Спочатку завантажте зображення карти.")
            return
        self.is_centering_mode = True
        self.set_cross_cursor()

    def set_cross_cursor(self):
        self.mapDisplayLabel.setCursor(Qt.CursorShape.CrossCursor)
        self.centerCircleLabel.setCursor(Qt.CursorShape.CrossCursor)
        self.centerPointIconLabel.setCursor(Qt.CursorShape.CrossCursor)

    def clear_cross_cursor(self):
        self.mapDisplayLabel.setCursor(Qt.CursorShape.ArrowCursor)
        self.centerCircleLabel.setCursor(Qt.CursorShape.ArrowCursor)
        self.centerPointIconLabel.setCursor(Qt.CursorShape.ArrowCursor)

    def on_zoom_in(self):
        print("[on_zoom_in] Збільшення масштабу")
        self.scaleSpinBox.setValue(self.scaleSpinBox.value() + 1)

    def on_zoom_out(self):
        print("[on_zoom_out] Зменшення масштабу")
        self.scaleSpinBox.setValue(self.scaleSpinBox.value() - 1)

    def on_scale_changed(self, value):
        print(f"[on_scale_changed] Масштаб змінено: {value}%")
        self.update_map_display()

    def update_map_display(self):
        print("[update_map_display] Оновлення зображення карти...")
        if not self.original_pixmap:
            print("[update_map_display] Немає зображення для відображення — очищаю фон")
            bg_pixmap = QPixmap(self.mapDisplayLabel.size())
            bg_pixmap.fill(Qt.GlobalColor.transparent)
            self.mapDisplayLabel.setPixmap(bg_pixmap)
            return

        self.current_scale = self.scaleSpinBox.value() / 100.0
        # ... (решта коду update_map_display залишається такою ж)

        scaled_pixmap = self.original_pixmap.scaled(
            int(self.original_pixmap.width() * self.current_scale),
            int(self.original_pixmap.height() * self.current_scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        scaled_center_point = self.center_point * self.current_scale
        self.current_offset = self.screen_center - scaled_center_point

        display_pixmap = QPixmap(self.mapDisplayLabel.size())
        display_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(display_pixmap)
        painter.drawPixmap(self.current_offset, scaled_pixmap)
        painter.end()

        self.mapDisplayLabel.setPixmap(display_pixmap)
        print("[update_map_display] Відображення оновлено\n")

    def eventFilter(self, source, event):
        if (
            source is self.mapDisplayLabel
            or source is self.centerCircleLabel
            or source is self.centerPointIconLabel
        ):
            if event.type() == QEvent.Type.MouseButtonPress and self.is_centering_mode:
                if event.button() == Qt.MouseButton.LeftButton:
                    label_click_pos = source.mapTo(self.mapDisplayLabel, event.pos())
                    print(f"[eventFilter] Клік у режимі центрування: {label_click_pos}")
                    if self.current_scale == 0:
                        print(
                            "[eventFilter] ПОМИЛКА: масштаб 0 — неможливо обчислити координати"
                        )
                        return True

                    img_x = int(
                        (label_click_pos.x() - self.current_offset.x())
                        // self.current_scale
                    )
                    img_y = int(
                        (label_click_pos.y() - self.current_offset.y())
                        // self.current_scale
                    )
                    self.center_point = QPoint(img_x, img_y)
                    print(f"[eventFilter] Новий центр зображення: {self.center_point}")

                    self.is_centering_mode = False
                    self.clear_cross_cursor()
                    self.centerPointIconLabel.setVisible(True)
                    self.update_map_display()
                    return True

        return super().eventFilter(source, event)

    def save(self):
        """
        Цей метод тепер автоматично викликається при натисканні 'saveButton'.
        """
        print("[accept] Підтвердження та збереження налаштувань...")
        if not self.original_pixmap or not self.image_path:
            print("[accept] ПОМИЛКА: зображення не вибрано")
            QMessageBox.warning(None, "Помилка", "Зображення не вибрано!")
            return

        screen_circle_radius_px = self.centerCircleLabel.width() / 2
        user_defined_radius_m = self.radiusMetersSpinBox.value()
        current_view_scale = self.scaleSpinBox.value() / 100.0

        print(
            f"[accept] Радіус на екрані: {screen_circle_radius_px}px = {user_defined_radius_m}м"
        )
        print(f"[accept] Поточний масштаб перегляду: {current_view_scale}")

        if user_defined_radius_m <= 0 or current_view_scale <= 0:
            print("[accept] ПОМИЛКА: некоректні значення радіуса або масштабу")
            QMessageBox.warning(
                None, "Помилка", "Радіус в метрах та масштаб мають бути > 0."
            )
            return

        displayed_px_per_meter = screen_circle_radius_px / user_defined_radius_m
        original_px_per_meter = displayed_px_per_meter / current_view_scale
        print(f"[accept] Пікселів на метр (оригінал): {original_px_per_meter}")

        target_diameter_m = self.settings_service.radar_max_radius * 2
        target_size_px = int(round(target_diameter_m * original_px_per_meter))
        print(
            f"[accept] Цільовий розмір карти: {target_size_px}px ({target_diameter_m}м)"
        )

        if target_size_px <= 0:
            print("[accept] ПОМИЛКА: розраховано 0 або менше")
            QMessageBox.warning(
                None,
                "Помилка розрахунку",
                f"Цільовий розмір 0 або менше (розраховано: {target_size_px}px).",
            )
            return  # Не викликаємо super().accept()

        final_pixmap = QPixmap(
            int(target_size_px * self.add_sizes_map_k[0]),
            int(target_size_px * self.add_sizes_map_k[1]),
        )
        final_pixmap.fill(Qt.GlobalColor.transparent)
        print("[accept] Створено фінальну карту")

        final_center = QPoint(final_pixmap.width() // 2, final_pixmap.height() // 2)
        draw_pos_f = final_center - self.center_point
        print(f"[accept] Малювання оригіналу з позиції {draw_pos_f}")

        painter = QPainter(final_pixmap)
        painter.drawPixmap(draw_pos_f, self.original_pixmap)
        painter.end()
        print("[accept] Малювання завершено")

        # Зберігаємо налаштування у змінну класу
        self.result_settings = {
            "pixmap": final_pixmap,
            "px_per_meter": original_px_per_meter,
            # "total_diameter_meters": target_diameter_m,
            # "center_px_point": final_center_f.toPoint(),
        }

        print(f"[accept] Збережено налаштування: {self.result_settings}\n")

        self.accept()

    def cancel(self):
        """
        Цей метод автоматично викликається при натисканні 'cancelButton'.
        """
        print("[reject] Налаштування скасовано")

        # Очищуємо результат на випадок, якщо щось було
        self.result_settings = {}

        self.reject()

    def get_settings(self):
        """
        Новий метод: Головне вікно викликає це, щоб отримати результат.
        """
        return self.result_settings

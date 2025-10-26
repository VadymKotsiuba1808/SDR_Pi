import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt, QPoint, QEvent, QPointF, pyqtSignal
from PyQt6 import uic


class SetMapWindow(QMainWindow):
    # Сигнал, що відправляє словник з налаштуваннями при збереженні
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        print("[Init] Ініціалізація SetMapWindow...")

        # Зберігаємо цільовий радіус радару
        self.settings_service = settings

        uic.loadUi("app/ui/set_map_window.ui", self)
        print("[Init] UI завантажено")

        # Внутрішні змінні стану
        self.original_pixmap = None
        self.image_path = ""  # Зберігаємо шлях для перевірки
        self.center_point_f = QPointF()
        self.current_scale = 1.0
        self.current_offset = QPointF()
        self.is_centering_mode = False

        self.screen_center = QPointF(
            self.mapDisplayLabel.width() / 2, self.mapDisplayLabel.height() / 2
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
        self.settings = {}  # Словник для збереження результатів
        print("[Init] Ініціалізацію завершено\n")

    def connect_signals(self):
        self.selectImageButton.clicked.connect(self.on_select_image)
        self.setCenterButton.clicked.connect(self.on_set_center)
        self.zoomInButton.clicked.connect(self.on_zoom_in)
        self.zoomOutButton.clicked.connect(self.on_zoom_out)
        self.scaleSpinBox.valueChanged.connect(self.on_scale_changed)

        # Змінено з accept/reject на кастомні слоти
        self.saveButton.clicked.connect(self.on_save)
        self.cancelButton.clicked.connect(self.on_cancel)

    # --- Обробники подій ---

    def on_select_image(self):
        print("[on_select_image] Відкривається діалог вибору зображення...")
        file_path, _ = QFileDialog.getOpenFileName(
            None,
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
        self.center_point_f = QPointF(self.original_pixmap.rect().center())
        print(f"[on_select_image] Початковий центр зображення: {self.center_point_f}")
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
        print(f"[update_map_display] Поточний масштаб: {self.current_scale}")

        scaled_pixmap = self.original_pixmap.scaled(
            int(self.original_pixmap.width() * self.current_scale),
            int(self.original_pixmap.height() * self.current_scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        print(
            f"[update_map_display] Новий розмір зображення: {scaled_pixmap.width()}x{scaled_pixmap.height()}"
        )

        scaled_center_point_f = self.center_point_f * self.current_scale
        self.current_offset = self.screen_center - scaled_center_point_f
        print(f"[update_map_display] Поточний offset: {self.current_offset}")

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

                    img_x = (
                        label_click_pos.x() - self.current_offset.x()
                    ) / self.current_scale
                    img_y = (
                        label_click_pos.y() - self.current_offset.y()
                    ) / self.current_scale
                    self.center_point_f = QPointF(img_x, img_y)
                    print(
                        f"[eventFilter] Новий центр зображення: {self.center_point_f}"
                    )

                    self.is_centering_mode = False
                    self.clear_cross_cursor()
                    self.centerPointIconLabel.setVisible(True)
                    self.update_map_display()
                    return True

        return super().eventFilter(source, event)

    def on_save(self):
        """
        Слот для кнопки "Зберегти". Замінює логіку accept().
        """
        print("[on_save] Підтвердження та збереження налаштувань...")
        if not self.original_pixmap or not self.image_path:
            print("[on_save] ПОМИЛКА: зображення не вибрано")
            QMessageBox.warning(None, "Помилка", "Зображення не вибрано!")
            return

        screen_circle_radius_px = 500.0
        user_defined_radius_m = self.radiusMetersSpinBox.value()
        current_view_scale = self.scaleSpinBox.value() / 100.0

        print(
            f"[on_save] Радіус на екрані: {screen_circle_radius_px}px = {user_defined_radius_m}м"
        )
        print(f"[on_save] Поточний масштаб перегляду: {current_view_scale}")

        if user_defined_radius_m <= 0 or current_view_scale <= 0:
            print("[on_save] ПОМИЛКА: некоректні значення радіуса або масштабу")
            QMessageBox.warning(
                None, "Помилка", "Радіус в метрах та масштаб мають бути > 0."
            )
            return

        displayed_px_per_meter = screen_circle_radius_px / user_defined_radius_m
        original_px_per_meter = displayed_px_per_meter / current_view_scale
        print(f"[on_save] Пікселів на метр (оригінал): {original_px_per_meter}")

        target_diameter_m = self.settings_service.radar_max_radius * 2.0
        target_size_px = int(round(target_diameter_m * original_px_per_meter))
        print(
            f"[on_save] Цільовий розмір карти: {target_size_px}px ({target_diameter_m}м)"
        )

        if target_size_px <= 0:
            print("[on_save] ПОМИЛКА: розраховано 0 або менше")
            QMessageBox.warning(
                None,
                "Помилка розрахунку",
                f"Цільовий розмір 0 або менше (розраховано: {target_size_px}px).",
            )
            return

        final_pixmap = QPixmap(target_size_px, target_size_px)
        final_pixmap.fill(Qt.GlobalColor.transparent)
        print("[on_save] Створено фінальну карту")

        final_center_f = QPointF(
            final_pixmap.width() / 2.0, final_pixmap.height() / 2.0
        )
        draw_pos_f = final_center_f - self.center_point_f
        print(f"[on_save] Малювання оригіналу з позиції {draw_pos_f}")

        painter = QPainter(final_pixmap)
        painter.drawPixmap(draw_pos_f, self.original_pixmap)
        painter.end()
        print("[on_save] Малювання завершено")

        self.settings = {
            "pixmap": final_pixmap,
            "px_per_meter": original_px_per_meter,
            "total_diameter_meters": target_diameter_m,
            "center_px_point": final_center_f.toPoint(),
        }

        print(f"[on_save] Збережено налаштування: {self.settings}\n")

        # Відправляємо сигнал з даними
        self.settings_saved.emit(self.settings)
        print(f"[on_save] Сигнал settings_saved відправлено")

        # Закриваємо вікно
        self.close()

    def on_cancel(self):
        """
        Слот для кнопки "Скасувати". Замінює логіку reject().
        """
        print("[on_cancel] Налаштування скасовано")
        self.close()

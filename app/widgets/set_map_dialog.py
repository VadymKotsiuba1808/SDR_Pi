import sys
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QPainter, QAction, QCursor
from PyQt6.QtCore import Qt, QPoint, QEvent, QPointF
from PyQt6 import uic


class SetMapDialog(QDialog):

    def __init__(self, settings, parent=None):
        super().__init__(parent)

        # Зберігаємо цільовий радіус радару
        self.settings_service = settings

        uic.loadUi("app/ui/set_map_dialog.ui", self)

        # Внутрішні змінні стану
        self.original_pixmap = None
        self.image_path = ""  # Зберігаємо шлях для перевірки в accept
        self.center_point_f = QPointF()
        self.current_scale = 1.0
        self.current_offset = QPoint()
        self.is_centering_mode = False

        self.screen_center = QPoint(
            self.mapDisplayLabel.width() // 2, self.mapDisplayLabel.height() // 2
        )

        self.connect_signals()
        self.mapDisplayLabel.installEventFilter(self)
        self.settings = {}

    def connect_signals(self):
        # ... (код connect_signals залишається без змін) ...
        self.selectImageButton.clicked.connect(self.on_select_image)
        self.setCenterButton.clicked.connect(self.on_set_center)
        self.zoomInButton.clicked.connect(self.on_zoom_in)
        self.zoomOutButton.clicked.connect(self.on_zoom_out)
        self.scaleSpinBox.valueChanged.connect(self.on_scale_changed)
        self.saveButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    # --- Обробники подій (залишаються без змін) ---

    def on_select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Виберіть зображення карти",
            "",
            "Зображення (*.png *.jpg *.bmp *.jpeg)",
        )

        if file_path:
            self.image_path = file_path  # Зберігаємо шлях
            self.original_pixmap = QPixmap(self.image_path)

            if self.original_pixmap.isNull():
                QMessageBox.warning(
                    self, "Помилка", f"Не вдалося завантажити зображення: {file_path}"
                )
                self.original_pixmap = None
                self.image_path = ""
                return

            self.center_point_f = QPointF(self.original_pixmap.rect().center())
            self.scaleSpinBox.setValue(100)
            self.centerPointIconLabel.setVisible(False)
            self.update_map_display()

    def on_set_center(self):
        if not self.original_pixmap:
            QMessageBox.warning(self, "Увага", "Спочатку завантажте зображення карти.")
            return
        self.is_centering_mode = True
        self.mapDisplayLabel.setCursor(Qt.CursorShape.CrossCursor)

    def on_zoom_in(self):
        self.scaleSpinBox.setValue(self.scaleSpinBox.value() + 1)

    def on_zoom_out(self):
        self.scaleSpinBox.setValue(self.scaleSpinBox.value() - 1)

    def on_scale_changed(self, value):
        self.update_map_display()

    def update_map_display(self):
        if not self.original_pixmap:
            # Очищуємо екран, якщо зображення немає
            bg_pixmap = QPixmap(self.mapDisplayLabel.size())
            bg_pixmap.fill(Qt.GlobalColor.black)
            self.mapDisplayLabel.setPixmap(bg_pixmap)
            return

        self.current_scale = self.scaleSpinBox.value() / 100.0

        scaled_pixmap = self.original_pixmap.scaled(
            (self.original_pixmap.size().toPointF() * self.current_scale).toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        scaled_center_point_f = self.center_point_f * self.current_scale
        self.current_offset = (self.screen_center - scaled_center_point_f).toPoint()

        display_pixmap = QPixmap(self.mapDisplayLabel.size())
        display_pixmap.fill(Qt.GlobalColor.black)

        painter = QPainter(display_pixmap)
        painter.drawPixmap(self.current_offset, scaled_pixmap)
        painter.end()

        self.mapDisplayLabel.setPixmap(display_pixmap)

    def eventFilter(self, source, event):
        if source is self.mapDisplayLabel:
            if event.type() == QEvent.Type.MouseButtonPress and self.is_centering_mode:
                if event.button() == Qt.MouseButton.LeftButton:
                    label_click_pos = event.pos()

                    # Перевіряємо, чи self.current_scale не нуль, щоб уникнути ділення на нуль
                    if self.current_scale == 0:
                        return True

                    img_x = (
                        label_click_pos.x() - self.current_offset.x()
                    ) / self.current_scale
                    img_y = (
                        label_click_pos.y() - self.current_offset.y()
                    ) / self.current_scale

                    self.center_point_f = QPointF(img_x, img_y)

                    self.is_centering_mode = False
                    self.mapDisplayLabel.setCursor(Qt.CursorShape.ArrowCursor)
                    self.centerPointIconLabel.setVisible(True)
                    self.update_map_display()

                    return True
        return super().eventFilter(source, event)

    # 2. ОСНОВНА ОНОВЛЕНА ЛОГІКА ТУТ
    def accept(self):
        """
        Перевизначено, щоб зібрати, розрахувати та
        повернути фінальний QPixmap.
        """

        # Перевіряємо, чи завантажено зображення
        if not self.original_pixmap or not self.image_path:
            QMessageBox.warning(self, "Помилка", "Зображення не вибрано!")
            return  # Не закриваємо вікно

        # 1. Отримуємо калібрувальні дані
        # Радіус кола в UI (жорстко заданий в .ui як 1000x1000 -> R=500)
        screen_circle_radius_px = 500.0
        # Скільком метрам він відповідає (задано користувачем)
        user_defined_radius_m = self.radiusMetersSpinBox.value()
        # Поточний масштаб ПЕРЕГЛЯДУ (зум)
        current_view_scale = self.scaleSpinBox.value() / 100.0

        if user_defined_radius_m <= 0 or current_view_scale <= 0:
            QMessageBox.warning(
                self, "Помилка", "Радіус в метрах та масштаб мають бути > 0."
            )
            return

        # 2. Розраховуємо "золотий" коефіцієнт: пікселів на метр
        #    на ОРИГІНАЛЬНОМУ (100%) зображенні.

        # (A) Скільки пікселів на екрані припадає на 1 метр
        displayed_px_per_meter = screen_circle_radius_px / user_defined_radius_m

        # (B) Конвертуємо в пікселі ОРИГІНАЛЬНОГО зображення
        original_px_per_meter = displayed_px_per_meter / current_view_scale

        # 3. Розраховуємо цільовий розмір (в пікселях) для фінальної карти
        #    Цільова карта має покривати діаметр = radar_max_radius * 2

        # Цільовий діаметр (ширина/висота) в метрах
        target_diameter_m = self.settings_service.radar_max_radius * 2.0

        # Цільовий діаметр (ширина/висота) в пікселях
        target_size_px = int(round(target_diameter_m * original_px_per_meter))

        if target_size_px <= 0:
            QMessageBox.warning(
                self,
                "Помилка розрахунку",
                f"Цільовий розмір 0 або менше (розраховано: {target_size_px}px). Перевірте введені дані.",
            )
            return

        # 4. Створюємо нову (фінальну) QPixmap
        final_pixmap = QPixmap(target_size_px, target_size_px)
        # Заливаємо прозорим фоном (виконує роль padding)
        final_pixmap.fill(Qt.GlobalColor.transparent)

        # 5. Визначаємо, куди на ній намалювати оригінальну карту
        # Центр нової (фінальної) карти
        final_center_f = QPointF(
            final_pixmap.width() / 2.0, final_pixmap.height() / 2.0
        )

        # self.center_point_f - це точка (в коорд. оригіналу),
        # яка має опинитись в final_center_f

        # Позиція (top-left) для малювання оригіналу:
        draw_pos_f = final_center_f - self.center_point_f

        # 6. Малюємо
        painter = QPainter(final_pixmap)
        painter.drawPixmap(draw_pos_f, self.original_pixmap)
        # QPainter автоматично обріже (crop), якщо original_pixmap
        # виходить за межі final_pixmap
        painter.end()

        # 7. Зберігаємо фінальні, оброблені налаштування
        self.settings = {
            "pixmap": final_pixmap,
            "px_per_meter": original_px_per_meter,
            "total_diameter_meters": target_diameter_m,
            "center_px_point": final_center_f.toPoint(),
        }

        print("Налаштування оброблено та збережено:", self.settings)
        super().accept()  # Закриваємо вікно

    def reject(self):
        print("Налаштування скасовано")
        super().reject()

    def get_settings(self):
        return self.settings

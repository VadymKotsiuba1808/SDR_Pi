import sys

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtGui import QPixmap, QPainter, QTransform
from PyQt6.QtCore import Qt, QEvent, QPointF
from PyQt6 import uic

from app.protocols import SetMapDialogSettings


class SetMapDialog(QDialog):

    def __init__(
        self, settings: SetMapDialogSettings, add_sizes_map_k=[1, 1], parent=None
    ):
        super().__init__(parent)
        print("[Init] Ініціалізація SetMapDialog...")

        # Зберігаємо цільовий радіус радару
        self.settings_service = settings
        self.add_sizes_map_k = add_sizes_map_k

        # Завантажуємо .ui файл
        uic.loadUi("app/ui/set_map_dialog.ui", self)
        print("[Init] UI завантажено")

        # Внутрішні змінні стану
        self.original_pixmap = None
        self.image_path = ""
        self.current_scale = 1.0
        self.current_rotation = 0.0  # Нова змінна для обертання

        # --- ВИПРАВЛЕННЯ: Повертаємо QPointF для точності ---
        self.center_point_f = QPointF()
        self.current_offset_f = QPointF()
        # ---

        self.is_centering_mode = False
        circle_radius = self.centerCircleLabel.width() / 2

        # --- ВИПРАВЛЕННЯ: Повертаємо QPointF ---
        self.screen_center_f = QPointF(
            self.centerCircleLabel.x() + circle_radius,
            self.centerCircleLabel.y() + circle_radius,
        )
        # ---

        print(
            f"[Init] Розмір екрану карти: {self.mapDisplayLabel.width()}x{self.mapDisplayLabel.height()}"
        )
        print(f"[Init] Центр екрана карти: {self.screen_center_f}")

        self._connect_handlers()
        print("[Init] Сигнали підключено")

        self.mapDisplayLabel.installEventFilter(self)
        self.centerCircleLabel.installEventFilter(self)
        self.centerPointIconLabel.installEventFilter(self)

        # Це буде словник, який ми повернемо
        self.result_settings = {}
        print("[Init] Ініціалізацію завершено\n")

    def _connect_handlers(self):
        self.selectImageButton.clicked.connect(self.on_select_image)
        self.setCenterButton.clicked.connect(self.on_set_center)
        self.zoomInButton.clicked.connect(self.on_zoom_in)
        self.zoomOutButton.clicked.connect(self.on_zoom_out)
        self.scaleSpinBox.valueChanged.connect(self.on_scale_changed)
        self.rotateSpinBox.valueChanged.connect(self.on_rotation_changed)
        self.rotateIncreaseButton.clicked.connect(self.on_rotation_increase)
        self.rotateDecreaseButton.clicked.connect(self.on_rotation_decrease)

        # Підключаємо кнопки до вбудованих слотів QDialog
        self.saveButton.clicked.connect(self.save)
        self.cancelButton.clicked.connect(self.cancel)

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

        # --- ВИПРАВЛЕННЯ: Повертаємо QPointF ---
        self.center_point_f = QPointF(self.original_pixmap.rect().center())
        print(f"[on_select_image] Початковий центр зображення: {self.center_point_f}")
        # ---

        self.scaleSpinBox.setValue(100)
        self.rotateSpinBox.setValue(0)  # Скидаємо кут

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

    def on_rotation_changed(self, value):
        print(f"[on_rotation_changed] Кут змінено: {value}°")
        self.current_rotation = float(value)
        self.update_map_display()

    def on_rotation_increase(self):
        print("[on_rotation_increase] Збільшення кута")
        self.rotateSpinBox.setValue(self.rotateSpinBox.value() + 1)

    def on_rotation_decrease(self):
        print("[on_rotation_decrease] Зменшення кута")
        self.rotateSpinBox.setValue(self.rotateSpinBox.value() - 1)

    def update_map_display(self):
        print("[update_map_display] Оновлення зображення карти...")
        if not self.original_pixmap:
            print("[update_map_display] Немає зображення для відображення — очищаю фон")
            bg_pixmap = QPixmap(self.mapDisplayLabel.size())
            bg_pixmap.fill(Qt.GlobalColor.transparent)
            self.mapDisplayLabel.setPixmap(bg_pixmap)
            return

        self.current_scale = self.scaleSpinBox.value() / 100.0

        scaled_pixmap = self.original_pixmap.scaled(
            int(self.original_pixmap.width() * self.current_scale),
            int(self.original_pixmap.height() * self.current_scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # --- ВИПРАВЛЕННЯ: Повертаємо QPointF ---
        scaled_center_point_f = self.center_point_f * self.current_scale
        self.current_offset_f = self.screen_center_f - scaled_center_point_f
        # ---

        display_pixmap = QPixmap(self.mapDisplayLabel.size())
        display_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(display_pixmap)

        # --- ОНОВЛЕННЯ: Додаємо логіку обертання ---
        painter.save()  # Зберігаємо стан painter

        # 1. Переходимо до центру екрана (точка обертання)
        painter.translate(self.screen_center_f)
        # 2. Обертаємо
        painter.rotate(self.current_rotation)
        # 3. Повертаємось
        painter.translate(-self.screen_center_f)

        # 4. Малюємо pixmap з його зсувом (збереженим у QPointF)
        painter.drawPixmap(self.current_offset_f, scaled_pixmap)

        painter.restore()  # Відновлюємо стан (скасовуємо translate/rotate)
        # --- КІНЕЦЬ ОНОВЛЕННЯ ---

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

                    # --- ОНОВЛЕННЯ: Математика для обертання ---

                    # 1. Отримуємо позицію кліку (у координатах mapDisplayLabel)
                    label_click_pos_f = QPointF(
                        source.mapTo(self.mapDisplayLabel, event.pos())
                    )
                    print(
                        f"[eventFilter] Клік у режимі центрування: {label_click_pos_f}"
                    )

                    if self.current_scale == 0:
                        print("[eventFilter] ПОМИЛКА: масштаб 0")
                        return True

                    # 2. Створюємо "зворотну" трансформацію
                    transform = QTransform()
                    # 2a. Переходимо до точки обертання
                    transform.translate(
                        self.screen_center_f.x(), self.screen_center_f.y()
                    )
                    # 2b. Обертаємо у ЗВОРОТНИЙ бік
                    transform.rotate(-self.current_rotation)
                    # 2c. Повертаємось
                    transform.translate(
                        -self.screen_center_f.x(), -self.screen_center_f.y()
                    )

                    # 3. Застосовуємо зворотну трансформацію до точки кліку
                    unrotated_click_pos_f = transform.map(label_click_pos_f)

                    # 4. Тепер розраховуємо координати на зображенні (стара логіка)
                    img_x = (
                        unrotated_click_pos_f.x() - self.current_offset_f.x()
                    ) / self.current_scale
                    img_y = (
                        unrotated_click_pos_f.y() - self.current_offset_f.y()
                    ) / self.current_scale

                    self.center_point_f = QPointF(img_x, img_y)
                    print(
                        f"[eventFilter] Новий центр зображення: {self.center_point_f}"
                    )
                    # --- КІНЕЦЬ ОНОВЛЕННЯ ---

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
            return  # Важливо: не викликаємо super().accept()

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
            return  # Не викликаємо super().accept()

        displayed_px_per_meter = screen_circle_radius_px / user_defined_radius_m
        original_px_per_meter = displayed_px_per_meter / current_view_scale
        print(f"[accept] Пікселів на метр (оригінал): {original_px_per_meter}")

        target_diameter_m = self.settings_service.radar_max_radius * 2
        target_size_px = int(round(target_diameter_m * original_px_per_meter))
        print(
            f"[accept] Цільовий розмір карти: {target_size_px}px ({target_diameter_m}м)"
        )

        if target_size_px <= 0:
            # ... (обробка помилки) ...
            return

        final_pixmap = QPixmap(
            int(target_size_px * self.add_sizes_map_k[0]),
            int(target_size_px * self.add_sizes_map_k[1]),
        )
        final_pixmap.fill(Qt.GlobalColor.transparent)
        print("[accept] Створено фінальну карту")

        final_center_f = QPointF(
            final_pixmap.width() / 2.0, final_pixmap.height() / 2.0
        )

        painter = QPainter(final_pixmap)

        # --- ОНОВЛЕННЯ: Обертання при збереженні ---
        # 1. Переходимо до центру фінального зображення
        painter.translate(final_center_f)
        # 2. Обертаємо канву
        painter.rotate(self.current_rotation)
        # 3. Малюємо оригінальний pixmap, зсунувши його на його центр
        # (щоб 'center_point_f' опинився в 'final_center_f')
        painter.drawPixmap(-self.center_point_f, self.original_pixmap)
        # --- КІНЕЦЬ ОНОВЛЕННЯ ---

        painter.end()
        print("[accept] Малювання завершено")

        # Зберігаємо налаштування у змінну класу
        self.result_settings = {
            "pixmap": final_pixmap,
            "px_per_meter": original_px_per_meter,
            "rotation": self.current_rotation,  # Додаємо кут
            "total_diameter_meters": target_diameter_m,  # Розкоментував
            "center_px_point": final_center_f.toPoint(),  # Розкоментував
        }

        print(f"[accept] Збережено налаштування\n")

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

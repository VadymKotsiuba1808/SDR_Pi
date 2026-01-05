"""
Діалог налаштування мапи.
Дозволяє користувачу вибрати та налаштувати власне зображення мапи.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtGui import QPixmap, QPainter, QTransform
from PyQt6.QtCore import Qt, QEvent, QPointF, QCoreApplication, QTranslator

from PyQt6 import uic

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.protocols import SetMapDialogSettings
from app.ui.ui_set_map_dialog import Ui_SetMapDialog


class SetMapDialog(QDialog):

    def __init__(
        self, settings: SetMapDialogSettings, add_sizes_map_k=[1, 1], parent=None
    ):
        super().__init__(parent)
        print("[Init] Ініціалізація SetMapDialog...")

        self.settings_service = settings
        self.add_sizes_map_k = add_sizes_map_k

        self._load_ui()
        print("[Init] UI завантажено")

        self._setup_state_variables()
        print(
            f"[Init] Розмір екрану карти: {self.ui.mapDisplayLabel.width()}x{self.ui.mapDisplayLabel.height()}"
        )
        print(f"[Init] Центр екрана карти: {self.screen_center_f}")

        self._adjust_fields()
        self._connect_handlers()
        print("[Init] Сигнали підключено")

        self._load_language()

        print("[Init] Ініціалізацію завершено\n")

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                print("Зміна мови, оновлюю UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self):
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_SetMapDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/set_map_dialog.ui", self)
            self.ui = self

    def _setup_state_variables(self):
        self.original_pixmap = None
        self.image_path = ""
        self.current_scale = 1.0
        self.current_rotation = 0.0

        self.center_point_f = QPointF()
        self.current_offset_f = QPointF()

        self.is_centering_mode = False
        circle_radius = self.ui.centerCircleLabel.width() / 2

        self.screen_center_f = QPointF(
            self.ui.centerCircleLabel.x() + circle_radius,
            self.ui.centerCircleLabel.y() + circle_radius,
        )

        self.result_settings = {}
        self.translator = QTranslator()

    def _adjust_fields(self):
        self.ui.mapDisplayLabel.installEventFilter(self)
        self.ui.centerCircleLabel.installEventFilter(self)

    def _connect_handlers(self):
        self.ui.selectImageButton.clicked.connect(self.handle_select_image)
        self.ui.setCenterButton.clicked.connect(self.handle_set_center)
        self.ui.zoomInButton.clicked.connect(self.handle_zoom_in)
        self.ui.zoomOutButton.clicked.connect(self.handle_zoom_out)
        self.ui.scaleSpinBox.valueChanged.connect(self.handle_scale_changed)
        self.ui.rotateSpinBox.valueChanged.connect(self.handle_rotation_changed)
        self.ui.rotateHorizontalSlider.valueChanged.connect(
            self.handle_rotation_changed
        )

        self.ui.saveButton.clicked.connect(self.handle_save)
        self.ui.cancelButton.clicked.connect(self.handle_cancel)

    def _load_language(self):
        # Видаляємо старий перекладач
        lang_code = self.settings_service.lang_code

        if lang_code == None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    def handle_select_image(self):
        print("[on_select_image] Відкривається діалог вибору зображення...")
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            self.tr("Виберіть зображення карти"),
            "",
            self.tr("Зображення (*.png *.jpg *.bmp *.jpeg)"),
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
                None, self.tr("Помилка"), self.tr("Не вдалося завантажити зображення.")
            )
            self.original_pixmap = None
            self.image_path = ""
            return

        print(
            f"[on_select_image] Зображення завантажено, розмір: {self.original_pixmap.width()}x{self.original_pixmap.height()}"
        )

        self.center_point_f = QPointF(self.original_pixmap.rect().center())
        print(f"[on_select_image] Початковий центр зображення: {self.center_point_f}")

        self.ui.scaleSpinBox.setValue(100)
        self.ui.rotateSpinBox.setValue(0)

        self.update_map_display()

    def handle_set_center(self):
        print("[on_set_center] Активовано режим вибору центру")
        if not self.original_pixmap:
            QMessageBox.warning(
                None, self.tr("Увага"), self.tr("Спочатку завантажте зображення карти.")
            )
            return
        self.is_centering_mode = True
        self.set_cross_cursor()

    def set_cross_cursor(self):
        self.ui.mapDisplayLabel.setCursor(Qt.CursorShape.CrossCursor)
        self.ui.centerCircleLabel.setCursor(Qt.CursorShape.CrossCursor)

    def clear_cross_cursor(self):
        self.ui.mapDisplayLabel.setCursor(Qt.CursorShape.ArrowCursor)
        self.ui.centerCircleLabel.setCursor(Qt.CursorShape.ArrowCursor)

    def handle_zoom_in(self):
        print("[on_zoom_in] Збільшення масштабу")
        self.ui.scaleSpinBox.setValue(self.ui.scaleSpinBox.value() + 1)

    def handle_zoom_out(self):
        print("[on_zoom_out] Зменшення масштабу")
        self.ui.scaleSpinBox.setValue(self.ui.scaleSpinBox.value() - 1)

    def handle_scale_changed(self, value):
        print(f"[on_scale_changed] Масштаб змінено: {value}%")
        self.update_map_display()

    def handle_rotation_changed(self, value):
        print(f"[on_rotation_changed] Кут змінено: {value}°")

        # Визначаємо, хто викликав зміну (спінбокс чи слайдер)
        sender = self.sender()

        # Синхронізуємо значення, не викликаючи повторних сигналів
        if sender == self.ui.rotateSpinBox:
            self.ui.rotateHorizontalSlider.blockSignals(True)
            self.ui.rotateHorizontalSlider.setValue(value)
            self.ui.rotateHorizontalSlider.blockSignals(False)
        elif sender == self.ui.rotateHorizontalSlider:
            self.ui.rotateSpinBox.blockSignals(True)
            self.ui.rotateSpinBox.setValue(value)
            self.ui.rotateSpinBox.blockSignals(False)

        # Зберігаємо поточний кут
        self.current_rotation = float(value)

        # Оновлюємо карту
        self.update_map_display()

    def update_map_display(self):
        print("[update_map_display] Оновлення зображення карти...")
        if not self.original_pixmap:
            print("[update_map_display] Немає зображення для відображення — очищаю фон")
            bg_pixmap = QPixmap(self.ui.mapDisplayLabel.size())
            bg_pixmap.fill(Qt.GlobalColor.transparent)
            self.ui.mapDisplayLabel.setPixmap(bg_pixmap)
            return

        self.current_scale = self.ui.scaleSpinBox.value() / 100.0

        scaled_pixmap = self.original_pixmap.scaled(
            int(self.original_pixmap.width() * self.current_scale),
            int(self.original_pixmap.height() * self.current_scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        scaled_center_point_f = self.center_point_f * self.current_scale
        self.current_offset_f = self.screen_center_f - scaled_center_point_f
        # ---

        display_pixmap = QPixmap(self.ui.mapDisplayLabel.size())
        display_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(display_pixmap)

        painter.save()

        painter.translate(self.screen_center_f)
        painter.rotate(self.current_rotation)
        painter.translate(-self.screen_center_f)

        painter.drawPixmap(self.current_offset_f, scaled_pixmap)

        painter.restore()

        painter.end()

        self.ui.mapDisplayLabel.setPixmap(display_pixmap)
        print("[update_map_display] Відображення оновлено\n")

    def eventFilter(self, source, event):
        if source is self.ui.mapDisplayLabel or source is self.ui.centerCircleLabel:
            if event.type() == QEvent.Type.MouseButtonPress and self.is_centering_mode:
                if event.button() == Qt.MouseButton.LeftButton:

                    # 1. Отримуємо позицію кліку (у координатах mapDisplayLabel)
                    label_click_pos_f = QPointF(
                        source.mapTo(self.ui.mapDisplayLabel, event.pos())
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
                    self.update_map_display()
                    return True

        return super().eventFilter(source, event)

    def handle_save(self):
        """
        Цей метод тепер автоматично викликається при натисканні 'saveButton'.
        """
        print("[accept] Підтвердження та збереження налаштувань...")
        if not self.original_pixmap or not self.image_path:
            print("[accept] ПОМИЛКА: зображення не вибрано")
            QMessageBox.warning(
                None, self.tr("Помилка"), self.tr("Зображення не вибрано!")
            )
            return  # Важливо: не викликаємо super().accept()

        screen_circle_radius_px = self.ui.centerCircleLabel.width() / 2
        user_defined_radius_km = self.ui.radiusKmDoubleSpinBox.value()
        current_view_scale = self.ui.scaleSpinBox.value() / 100.0

        print(
            f"[accept] Радіус на екрані: {screen_circle_radius_px}px = {user_defined_radius_km}км"
        )
        print(f"[accept] Поточний масштаб перегляду: {current_view_scale}")

        if user_defined_radius_km <= 0 or current_view_scale <= 0:
            print("[accept] ПОМИЛКА: некоректні значення радіуса або масштабу")
            QMessageBox.warning(
                None,
                self.tr("Помилка"),
                self.tr("Радіус в метрах та масштаб мають бути > 0."),
            )
            return  # Не викликаємо super().accept()

        displayed_px_per_km = screen_circle_radius_px / user_defined_radius_km
        original_px_per_km = displayed_px_per_km / current_view_scale
        print(f"[accept] Пікселів на км (оригінал): {original_px_per_km}")

        target_diameter_km = self.settings_service.radar_max_radius_km * 2
        target_size_px = int(round(target_diameter_km * original_px_per_km))
        print(
            f"[accept] Цільовий розмір карти: {target_size_px}px ({target_diameter_km}км)"
        )

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
            "px_per_meter": original_px_per_km,
            "rotation": self.current_rotation,
            "total_diameter_km": target_diameter_km,
            "center_px_point": final_center_f.toPoint(),
        }

        print(f"[accept] Збережено налаштування\n")

        self.accept()

    def handle_cancel(self):
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

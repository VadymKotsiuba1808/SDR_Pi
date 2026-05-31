"""
Діалог налаштування мапи.
Дозволяє користувачу вибрати та налаштувати власне зображення мапи.
"""

from typing import List, Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import (
    QCoreApplication,
    QEvent,
    QObject,
    QPointF,
    Qt,
    QTranslator,
)
from PyQt6.QtGui import QMouseEvent, QPainter, QPixmap, QTransform
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
)

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.core.mixins import TestUIOptimizationMixin
from app.models.map_settings import CustomMapSettings
from app.protocols import SetMapDialogSettings
from app.ui.ui_set_map_dialog import Ui_SetMapDialog


class SetMapDialog(QDialog, TestUIOptimizationMixin):
    def __init__(
        self,
        settings: SetMapDialogSettings,
        add_sizes_map_k: List[float] = [1, 1],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        print("[Init] Ініціалізація SetMapDialog...")

        self.settings_service = settings
        self.add_sizes_map_k = add_sizes_map_k

        self._load_ui()
        print("[Init] UI завантажено")

        self._setup_variables()
        self._calculate_screen_center()

        self._adjust_fields()
        self._connect_handlers()
        self._load_language()
        self.apply_test_ui_optimization()

    def _calculate_screen_center(self):
        """
        Знаходить точні координати центру радара (червоного кола) відносно мапи.
        """
        # Геометрія кола відносно батьківського вікна
        circle_geo = self.ui.centerCircleLabel.geometry()

        # Центр кола
        cx = circle_geo.x() + (circle_geo.width() / 2)
        cy = circle_geo.y() + (circle_geo.height() / 2)

        self.screen_center_f = QPointF(cx, cy)

    def changeEvent(self, a0: QEvent | None) -> None:
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self):
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_SetMapDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/set_map_dialog.ui", self)
            self.ui = cast(Ui_SetMapDialog, self)

    def _setup_variables(self) -> None:
        self.original_pixmap: Optional[QPixmap] = None
        self.image_path: str = ""
        self.current_scale: float = 1.0
        self.current_rotation: float = 0.0
        self.center_point_f = QPointF()
        self.is_centering_mode: bool = False
        self.result_settings: Optional[CustomMapSettings] = None
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
        lang_code = self.settings_service.lang_code
        if not lang_code:
            return
        QCoreApplication.removeTranslator(self.translator)
        if self.translator.load(f"app/i18n/qm/app_{lang_code}.qm"):
            QCoreApplication.installTranslator(self.translator)

    # --- ЛОГІКА МАТРИЦЬ ---

    def _get_transform_matrix(self) -> QTransform:
        """
        Єдина матриця трансформації.
        """
        t = QTransform()
        t.translate(self.screen_center_f.x(), self.screen_center_f.y())
        t.rotate(self.current_rotation)
        t.scale(self.current_scale, self.current_scale)
        t.translate(-self.center_point_f.x(), -self.center_point_f.y())
        return t

    def update_map_display(self):
        if not self.original_pixmap:
            self.ui.mapDisplayLabel.clear()
            return

        self.current_scale = self.ui.scaleSpinBox.value() / 100.0

        canvas = QPixmap(self.ui.mapDisplayLabel.size())
        canvas.fill(Qt.GlobalColor.transparent)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setTransform(self._get_transform_matrix())
        painter.drawPixmap(0, 0, self.original_pixmap)
        painter.end()

        self.ui.mapDisplayLabel.setPixmap(canvas)

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        """
        Обробляє клік по карті або колу.
        Використовує ГЛОБАЛЬНІ координати для уникнення помилок зміщення.
        """
        source = a0
        event = a1

        if not source or not event:
            return super().eventFilter(source, event)

        if (
            (source is self.ui.mapDisplayLabel or source is self.ui.centerCircleLabel)
            and isinstance(event, QMouseEvent)
            and self.is_centering_mode
        ):
            if event.button() == Qt.MouseButton.LeftButton:
                if self.current_scale == 0:
                    return True

                global_pos = event.globalPosition().toPoint()

                local_pos_point = self.ui.mapDisplayLabel.mapFromGlobal(global_pos)
                screen_click_point = QPointF(local_pos_point)

                matrix = self._get_transform_matrix()
                inverted_matrix, invertible = matrix.inverted()

                if invertible:
                    image_click_point = inverted_matrix.map(screen_click_point)

                    print(
                        f"[Click Global] {global_pos} -> [Local] {local_pos_point} -> [Image] {image_click_point}"
                    )

                    self.center_point_f = image_click_point

                    self.is_centering_mode = False
                    self.clear_cross_cursor()
                    self.update_map_display()
                    return True

        return super().eventFilter(source, event)

    def handle_select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            self.tr("Оберіть карту"),
            "",
            self.tr("Image Files (*.png *.jpg *.jpeg *.bmp)"),
        )
        if not file_path:
            return

        self.image_path = file_path
        self.original_pixmap = QPixmap(self.image_path)

        if self.original_pixmap.isNull():
            QMessageBox.warning(None, self.tr("Error"), self.tr("Failed to load image"))
            return

        self.center_point_f = QPointF(self.original_pixmap.rect().center())

        self.ui.scaleSpinBox.setValue(100)
        self.ui.rotateSpinBox.setValue(0)
        self.update_map_display()

    def handle_set_center(self):
        if not self.original_pixmap:
            QMessageBox.warning(
                None, self.tr("Warning"), self.tr("Please load an image first")
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
        self.ui.scaleSpinBox.setValue(self.ui.scaleSpinBox.value() + 1)

    def handle_zoom_out(self):
        self.ui.scaleSpinBox.setValue(self.ui.scaleSpinBox.value() - 1)

    def handle_scale_changed(self, value):
        self.update_map_display()

    def handle_rotation_changed(self, value):
        sender = self.sender()
        if sender == self.ui.rotateSpinBox:
            self.ui.rotateHorizontalSlider.blockSignals(True)
            self.ui.rotateHorizontalSlider.setValue(value)
            self.ui.rotateHorizontalSlider.blockSignals(False)
        elif sender == self.ui.rotateHorizontalSlider:
            self.ui.rotateSpinBox.blockSignals(True)
            self.ui.rotateSpinBox.setValue(value)
            self.ui.rotateSpinBox.blockSignals(False)

        self.current_rotation = float(value)
        self.update_map_display()

    def handle_save(self):
        if not self.original_pixmap:
            return

        screen_radius = self.ui.centerCircleLabel.width() / 2
        real_radius_km = self.ui.radiusKmDoubleSpinBox.value()

        if real_radius_km <= 0 or self.current_scale <= 0:
            QMessageBox.warning(
                None, self.tr("Error"), self.tr("Invalid radius or scale")
            )
            return

        px_per_km_screen = screen_radius / real_radius_km
        px_per_km_original = px_per_km_screen / self.current_scale

        target_diameter_km = self.settings_service.radar_max_radius_km * 2
        target_size_px = int(round(target_diameter_km * px_per_km_original))

        if target_size_px > 12000:
            QMessageBox.critical(None, self.tr("Error"), self.tr("Image too large"))
            return

        final_w = int(target_size_px * self.add_sizes_map_k[0])
        final_h = int(target_size_px * self.add_sizes_map_k[1])
        final_pixmap = QPixmap(final_w, final_h)
        final_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        final_center = QPointF(final_w / 2, final_h / 2)

        t = QTransform()
        t.translate(final_center.x(), final_center.y())
        t.rotate(self.current_rotation)
        t.translate(-self.center_point_f.x(), -self.center_point_f.y())

        painter.setTransform(t)
        painter.drawPixmap(0, 0, self.original_pixmap)
        painter.end()

        self.result_settings = CustomMapSettings(
            pixmap=final_pixmap,
            px_per_km=px_per_km_original,
            rotation=self.current_rotation,
            total_diameter_km=target_diameter_km,
            center_px_point=final_center.toPoint(),
        )

        self.accept()

    def handle_cancel(self):
        self.result_settings = None
        self.reject()

    def get_settings(self) -> Optional[CustomMapSettings]:
        return self.result_settings

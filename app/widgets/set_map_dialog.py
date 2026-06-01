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
    """Діалогове вікно для налаштування власного зображення карти.

    Дозволяє користувачу завантажити зображення, встановити центр (позицію радара),
    масштабувати та обертати карту для точного відображення об'єктів.

    Attributes:
        settings_service (SetMapDialogSettings): Сервіс налаштувань для отримання мови та конфігурації.
        add_sizes_map_k (List[float]): Коефіцієнти додаткового розміру карти [ширина, висота].
        original_pixmap (Optional[QPixmap]): Початкове завантажене зображення без трансформацій.
        image_path (str): Абсолютний шлях до файлу зображення.
        current_scale (float): Поточний коефіцієнт масштабування (1.0 = 100%).
        current_rotation (float): Поточний кут повороту карти в градусах.
        center_point_f (QPointF): Координати вибраного центру (позиції радара) на оригінальному фото.
        screen_center_f (QPointF): Координати центру мішені на екрані відносно діалогу.
        is_centering_mode (bool): Чи активовано режим вибору центру за допомогою кліку миші.
        result_settings (Optional[CustomMapSettings]): Згенеровані налаштування та трансформована карта.
        translator (QTranslator): Перекладач для локалізації інтерфейсу.
    """

    def __init__(
        self,
        settings: SetMapDialogSettings,
        add_sizes_map_k: List[float] = [1, 1],
        parent=None,
    ) -> None:
        """Ініціалізує діалог налаштування карти.

        Args:
            settings: Об'єкт з налаштуваннями програми.
            add_sizes_map_k: Список з двох множників для фінального розміру карти.
            parent: Батьківський віджет.
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.settings_service = settings
        self.add_sizes_map_k = add_sizes_map_k

        self._load_ui()
        self._setup_variables()
        self._calculate_screen_center()

        self._adjust_fields()
        self._connect_handlers()
        self._load_language()
        self.apply_test_ui_optimization()

    def _calculate_screen_center(self) -> None:
        """Знаходить точні координати центру мішені (червоного кола) відносно віджета.

        Ці координати використовуються як точка прив'язки для візуальної трансформації
        карти на екрані.
        """
        circle_geo = self.ui.centerCircleLabel.geometry()

        # Розраховуємо центр відносно батьківського контейнера
        cx = circle_geo.x() + (circle_geo.width() / 2)
        cy = circle_geo.y() + (circle_geo.height() / 2)

        self.screen_center_f = QPointF(cx, cy)

    def changeEvent(self, a0: QEvent | None) -> None:
        """Обробляє зміну стану вікна, зокрема зміну мови інтерфейсу.

        Args:
            a0: Об'єкт події.
        """
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        """Завантажує інтерфейс користувача з .ui файлу або скомпільованого класу.

        Вибір методу завантаження залежить від константи `DEV_COMPILED_UI_USING_ENABLED`,
        що дозволяє гнучко працювати під час розробки та в релізі.
        """
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_SetMapDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/set_map_dialog.ui", self)
            self.ui = cast(Ui_SetMapDialog, self)

    def _setup_variables(self) -> None:
        """Ініціалізує початкові значення внутрішніх змінних стану."""
        self.original_pixmap: Optional[QPixmap] = None
        self.image_path: str = ""
        self.current_scale: float = 1.0
        self.current_rotation: float = 0.0
        self.center_point_f = QPointF()
        self.is_centering_mode: bool = False
        self.result_settings: Optional[CustomMapSettings] = None
        self.translator = QTranslator()

    def _adjust_fields(self) -> None:
        """Налаштовує додаткові параметри віджетів інтерфейсу."""
        self.ui.mapDisplayLabel.installEventFilter(self)
        self.ui.centerCircleLabel.installEventFilter(self)

    def _connect_handlers(self) -> None:
        """Підключає сигнали віджетів до відповідних методів-обробників."""
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

    def _load_language(self) -> None:
        """Завантажує та встановлює переклад інтерфейсу на основі налаштувань сервісу."""
        lang_code = self.settings_service.lang_code
        if not lang_code:
            return
        QCoreApplication.removeTranslator(self.translator)
        if self.translator.load(f"app/i18n/qm/app_{lang_code}.qm"):
            QCoreApplication.installTranslator(self.translator)

    def _get_transform_matrix(self) -> QTransform:
        """Створює матрицю трансформації для коректного відображення карти.

        Матриця забезпечує центрування вибраної точки `center_point_f` в центрі мішені,
        застосовуючи при цьому поточне масштабування та поворот.

        Returns:
            QTransform: Об'єкт матриці трансформації для QPainter.
        """
        t = QTransform()
        # Порядок операцій: зміщення в центр екрану -> поворот -> масштаб -> повернення в точку на фото
        t.translate(self.screen_center_f.x(), self.screen_center_f.y())
        t.rotate(self.current_rotation)
        t.scale(self.current_scale, self.current_scale)
        t.translate(-self.center_point_f.x(), -self.center_point_f.y())
        return t

    def update_map_display(self) -> None:
        """Оновлює візуальне відображення карти в інтерфейсі з урахуванням трансформацій.

        Малює карту на тимчасовому полотні (`canvas`) за допомогою `QPainter` з
        використанням матриці трансформації.
        """
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
        """Обробляє події миші для вибору центру карти.

        !!! note
            Для точності використовуються глобальні координати курсора (`globalPosition`).
            Це дозволяє уникнути помилок зміщення, коли клік потрапляє на `centerCircleLabel`,
            що знаходиться поверх основної мітки з картою.

        Args:
            a0: Об'єкт, що надіслав подію.
            a1: Об'єкт події.

        Returns:
            bool: True, якщо подію було перехоплено та оброблено.
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

                # Переводимо глобальні координати в локальні відносно мітки карти
                local_pos_point = self.ui.mapDisplayLabel.mapFromGlobal(global_pos)
                screen_click_point = QPointF(local_pos_point)

                # Використовуємо інвертовану матрицю для пошуку точки на ОРИГІНАЛЬНОМУ фото
                matrix = self._get_transform_matrix()
                inverted_matrix, invertible = matrix.inverted()

                if invertible:
                    image_click_point = inverted_matrix.map(screen_click_point)
                    self.center_point_f = image_click_point

                    self.is_centering_mode = False
                    self.clear_cross_cursor()
                    self.update_map_display()
                    return True

        return super().eventFilter(source, event)

    def handle_select_image(self) -> None:
        """Відкриває діалог вибору файлу та завантажує зображення карти."""
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

        # Початково встановлюємо центр у геометричний центр зображення
        self.center_point_f = QPointF(self.original_pixmap.rect().center())

        self.ui.scaleSpinBox.setValue(100)
        self.ui.rotateSpinBox.setValue(0)
        self.update_map_display()

    def handle_set_center(self) -> None:
        """Активує режим вибору центру карти кліком миші."""
        if not self.original_pixmap:
            QMessageBox.warning(
                None, self.tr("Warning"), self.tr("Please load an image first")
            )
            return
        self.is_centering_mode = True
        self.set_cross_cursor()

    def set_cross_cursor(self) -> None:
        """Встановлює курсор у формі перехрестя для точного вибору центру."""
        self.ui.mapDisplayLabel.setCursor(Qt.CursorShape.CrossCursor)
        self.ui.centerCircleLabel.setCursor(Qt.CursorShape.CrossCursor)

    def clear_cross_cursor(self) -> None:
        """Повертає стандартний курсор-стрілку."""
        self.ui.mapDisplayLabel.setCursor(Qt.CursorShape.ArrowCursor)
        self.ui.centerCircleLabel.setCursor(Qt.CursorShape.ArrowCursor)

    def handle_zoom_in(self) -> None:
        """Збільшує масштаб карти на 1%."""
        self.ui.scaleSpinBox.setValue(self.ui.scaleSpinBox.value() + 1)

    def handle_zoom_out(self) -> None:
        """Зменшує масштаб карти на 1%."""
        self.ui.scaleSpinBox.setValue(self.ui.scaleSpinBox.value() - 1)

    def handle_scale_changed(self, value: int) -> None:
        """Обробляє зміну значення масштабу.

        Args:
            value: Нове значення масштабу у відсотках.
        """
        self.update_map_display()

    def handle_rotation_changed(self, value: int) -> None:
        """Синхронізує значення слайдера та спінбокса для повороту карти.

        Args:
            value: Новий кут повороту в градусах.
        """
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

    def handle_save(self) -> None:
        """Генерує фінальне трансформоване зображення карти та зберігає налаштування.

        Розраховує реальний масштаб (пікселів на кілометр) та створює нове зображення,
        де вибраний центр знаходиться точно посередині полотна.

        !!! warning
            Максимальний розмір результуючого зображення обмежений 12000 пікселями для
            запобігання критичним помилкам пам'яті.
        """
        if not self.original_pixmap:
            return

        screen_radius = self.ui.centerCircleLabel.width() / 2
        real_radius_km = self.ui.radiusKmDoubleSpinBox.value()

        if real_radius_km <= 0 or self.current_scale <= 0:
            QMessageBox.warning(
                None, self.tr("Error"), self.tr("Invalid radius or scale")
            )
            return

        # Розрахунок фізичного масштабу
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

        # Будуємо матрицю для фінального рендеру (без масштабу, тільки поворот та зміщення центру)
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

    def handle_cancel(self) -> None:
        """Скасовує налаштування та закриває діалог."""
        self.result_settings = None
        self.reject()

    def get_settings(self) -> Optional[CustomMapSettings]:
        """Повертає об'єкт зі збереженими налаштуваннями карти.

        Returns:
            Optional[CustomMapSettings]: Налаштування карти або None, якщо діалог було скасовано.
        """
        return self.result_settings

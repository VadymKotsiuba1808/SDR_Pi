from typing import List, Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTranslator
from PyQt6.QtWidgets import (
    QDialog,
    QListWidgetItem,
    QMessageBox,
    QWidget,
)

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.core.logging_config import get_logger
from app.core.mixins import TestUIOptimizationMixin
from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, ServiceResponse
from app.protocols import LangSettings
from app.services.keyboard_service import KeyboardService
from app.services.pi_network_service import PiNetworkService
from app.ui.ui_class_manager_dialog import Ui_ClassManagerDialog
from app.widgets.keyboard_widget import KeyboardWidget

ALLOW_DB_OPERATIONS = [
    DbOperation.ADD_CLASS,
    DbOperation.UPDATE_CLASS,
    DbOperation.DELETE_CLASS,
    DbOperation.GET_CLASSES,
]


logger = get_logger(__name__)


class ClassManagerDialog(QDialog, TestUIOptimizationMixin):
    """
    Діалогове вікно для керування класами об'єктів.

    Забезпечує інтерфейс для CRUD операцій над класами об'єктів через мережевий сервіс.
    Підтримує зміну мови та інтеграцію з віртуальною клавіатурою.

    Attributes:
        network_service (PiNetworkService): Сервіс для взаємодії з сервером.
        settings_service (LangSettings): Сервіс налаштувань (мова тощо).
        keyboard_service (KeyboardService): Сервіс віртуальної клавіатури.
        ui (Ui_ClassManagerDialog): Згенерований або завантажений клас інтерфейсу.
    """

    def __init__(
        self,
        network_service: PiNetworkService,
        settings_service: LangSettings,
        keyboard_service: KeyboardService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        # Використовуємо FramelessWindowHint для кастомного дизайну без заголовків ОС
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.network_service = network_service
        self.settings_service = settings_service
        self.keyboard_service = keyboard_service

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()
        self._load_language()
        self.apply_test_ui_optimization()

    def changeEvent(self, a0: QEvent | None) -> None:
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_ClassManagerDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/class_manager_dialog.ui", self)
            self.ui = cast(Ui_ClassManagerDialog, self)

    def _setup_state_variables(self) -> None:
        self.translator = QTranslator()
        self.lang_widget = KeyboardWidget(
            self.settings_service, self.keyboard_service, parent=self
        )
        self._waiting_classes = False
        self.cached_classes: List[ObjectClass] = []

    def _adjust_fields(self) -> None:
        self.ui.keyboardLayout.addWidget(self.lang_widget)
        self._refresh_list()

    def _connect_handlers(self) -> None:
        self.ui.btnAdd.clicked.connect(self._handle_save)
        self.ui.btnDelete.clicked.connect(self._delete_class)
        self.ui.btnClose.clicked.connect(self.accept)
        self.ui.lstClasses.itemClicked.connect(self._on_item_clicked)

        self.network_service.request_finished.connect(self._handle_db_status)

        if hasattr(self.ui, "btnClearSelection"):
            self.ui.btnClearSelection.clicked.connect(self._clear_selection)

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return
        QCoreApplication.removeTranslator(self.translator)

    def _populate_list(self, classes: Optional[List[ObjectClass]] = None):
        if classes:
            self.cached_classes = classes

        self.ui.lstClasses.clear()
        # Сортуємо за назвою для зручності пошуку користувачем
        self.cached_classes.sort(key=lambda x: x.name)

        for c in self.cached_classes:
            item = QListWidgetItem(c.name)
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self.ui.lstClasses.addItem(item)

        self._clear_selection()

    def _refresh_list(self) -> None:
        self._waiting_classes = True
        self.network_service.request_db_classes()
        logger.debug("[ClassManager] Loaded classes.")

    def _handle_db_status(self, response: ServiceResponse) -> None:

        if response.operation not in ALLOW_DB_OPERATIONS:
            return

        if response.is_error:
            if response.operation == DbOperation.GET_CLASSES:
                if not self._waiting_classes:
                    return
                self._waiting_classes = False

            title = response.get_title()
            msg = response.get_message_or_default()

            QMessageBox.critical(self, title, msg)
            return

        match response.operation:
            case DbOperation.ADD_CLASS:
                if response.data:
                    self.add_cache_class(ObjectClass.from_dict(response.data))
            case DbOperation.UPDATE_CLASS | DbOperation.RENAME_CLASS:
                if response.data:
                    self.update_cache_class(ObjectClass.from_dict(response.data))
            case DbOperation.DELETE_CLASS:
                if isinstance(response.data, dict):
                    id = response.data.get("id")
                    if id:
                        self.delete_cache_class(id)
            case DbOperation.GET_CLASSES:
                if isinstance(response.data, dict):
                    classes_raw = response.data.get("classes", [])
                    classes_list = [ObjectClass.from_dict(c) for c in classes_raw]

                    if self._waiting_classes:
                        self._waiting_classes = False
                        self._populate_list(classes_list)

        logger.debug(f"[ObjectManager] DB Operation '{response.operation}': ...")

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.ui.inpClassName.setText(item.text())
        self.ui.btnAdd.setText(self.tr("Save"))

    def _clear_selection(self) -> None:
        self.ui.lstClasses.clearSelection()
        self.ui.inpClassName.clear()
        self.ui.btnAdd.setText(self.tr("Add"))

    def _handle_save(self) -> None:
        text = self.ui.inpClassName.text().strip()
        if not text:
            return

        selected_items = self.ui.lstClasses.selectedItems()

        if selected_items:
            # Режим редагування (перейменування)
            item = selected_items[0]
            old_name = item.text()

            if text == old_name:
                return

            logger.info(f"[ClassManager] Renaming class '{old_name}' to '{text}'...")
            # Шукаємо об'єкт у кеші за назвою
            index = next(
                (i for i, x in enumerate(self.cached_classes) if x.name == old_name),
                None,
            )
            if index is not None:
                old_class = self.cached_classes[index]
                new_class = ObjectClass(id=old_class.id, name=text)

                self.network_service.request_db_rename_class(old_class, new_class)

        else:
            # Режим додавання
            logger.info(f"[ClassManager] Adding new class '{text}'...")

            is_repeat = any(x.name == text for x in self.cached_classes)

            if is_repeat:
                QMessageBox.critical(
                    self,
                    self.tr("Warning"),
                    self.tr("Class with this name already exists."),
                )
                return

            new_class = ObjectClass(id=None, name=text)
            self.network_service.request_db_add_class(new_class)

    def _delete_class(self) -> None:
        item = self.ui.lstClasses.currentItem()
        if not item:
            QMessageBox.warning(
                self, self.tr("Warning"), self.tr("Select a class to delete.")
            )
            return

        class_name = item.text()
        class_id_data = item.data(Qt.ItemDataRole.UserRole)
        class_id = int(class_id_data) if class_id_data is not None else -1

        res = QMessageBox.question(
            self,
            self.tr("Delete"),
            self.tr("Delete class '{}'?").format(class_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if res == QMessageBox.StandardButton.Yes:
            logger.info(
                f"[ClassManager] Deleting class '{class_name}' (ID: {class_id})..."
            )

            self.network_service.request_db_delete_class(class_id)

    def add_cache_class(self, class_obj: ObjectClass):
        self.cached_classes.append(class_obj)
        self._populate_list()

    def update_cache_class(self, new_class_obj: ObjectClass):
        # Використовуємо next() з генератором для швидкого пошуку індексу за ID
        index = next(
            (i for i, x in enumerate(self.cached_classes) if x.id == new_class_obj.id),
            None,
        )

        if index is not None:
            self.cached_classes[index] = new_class_obj
            self._populate_list()

    def delete_cache_class(self, id: int):
        index = next((i for i, x in enumerate(self.cached_classes) if x.id == id), None)

        if index is not None:
            self.cached_classes.pop(index)
            self._populate_list()

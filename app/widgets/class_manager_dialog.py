from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog,
    QListWidgetItem,
    QMessageBox,
    QWidget,
)
from PyQt6 import uic
from PyQt6.QtCore import Qt, QEvent, QTranslator, QCoreApplication

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.ui.ui_class_manager_dialog import Ui_ClassManagerDialog
from app.widgets.keyboard_widget import KeyboardWidget
from app.services.keyboard_service import KeyboardService
from app.services.pi_network_service import PiNetworkService
from app.models.object_class import ObjectClass
from app.services.database_service import DatabaseService
from app.protocols import LangSettings


class ClassManagerDialog(QDialog):

    def __init__(
        self,
        network_service: PiNetworkService,
        settings_service: LangSettings,
        keyboard_service: KeyboardService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.network_service = network_service
        self.settings_service = settings_service
        self.keyboard_service = keyboard_service

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()
        self._load_language()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_ClassManagerDialog()
            self.ui.setupUi(self)
        else:
            ui_path = "app/ui/class_manager_dialog.ui"
            uic.loadUi(ui_path, self)
            self.ui = self

    def _setup_state_variables(self) -> None:
        self.translator = QTranslator()
        self.lang_widget = KeyboardWidget(
            self.settings_service, self.keyboard_service, parent=self
        )
        self.cached_classes: List[ObjectClass] = []

    def _adjust_fields(self) -> None:
        self.ui.keyboardLayout.addWidget(self.lang_widget)
        self._refresh_list()

    def _connect_handlers(self) -> None:
        self.ui.btnAdd.clicked.connect(self._handle_save)
        self.ui.btnDelete.clicked.connect(self._delete_class)
        self.ui.btnClose.clicked.connect(self.accept)
        self.ui.lstClasses.itemClicked.connect(self._on_item_clicked)

        self.network_service.db_operation_status.connect(self._handle_db_status)
        self.network_service.db_class_added.connect(self.add_cache_class)
        self.network_service.db_class_renamed.connect(self.update_cache_class)
        self.network_service.db_class_deleted.connect(self.delete_cache_class)

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

        for c in self.cached_classes:
            item = QListWidgetItem(c.name)
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self.ui.lstClasses.addItem(item)

        self._clear_selection()

    def _on_classes_received_for_list(self, classes: List[ObjectClass]):
        try:
            self.network_service.db_classes_received.disconnect(
                self._on_classes_received_for_list
            )
        except TypeError:
            pass

        self._populate_list(classes)

    def request_classes(self):
        self.network_service.db_classes_received.connect(
            self._on_classes_received_for_list
        )
        self.network_service.request_db_classes()

    def _refresh_list(self) -> None:

        self.request_classes()
        print(f"[ClassManager] Loaded classes.")

    def _handle_db_status(self, op_type: str, success: bool, msg: str) -> None:
        if success:
            return

        relevant_ops = ["add_class", "rename_class", "delete_class", "get_classes"]

        if op_type not in relevant_ops and op_type != "unknown":
            return

        # TODO - Додати переклад
        titles = {
            "add_class": "Помилка створення класу",
            "rename_class": "Помилка перейменування",
            "delete_class": "Помилка видалення",
            "get_classes": "Помилка завантаження списку",
            "unknown": "Системна помилка",
        }

        # TODO - Додати переклад
        title = titles.get(op_type, "Помилка операції")

        if op_type == "delete_class":
            # TODO - Додати переклад
            msg += "\nМожливо ваш клас використовується певними об'єктами"

        QMessageBox.critical(self, title, msg)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.ui.inpClassName.setText(item.text())
        # TODO - Додати переклад
        self.ui.btnAdd.setText("Зберегти")

    def _clear_selection(self) -> None:
        self.ui.lstClasses.clearSelection()
        self.ui.inpClassName.clear()
        # TODO - Додати переклад
        self.ui.btnAdd.setText("Додати")

    def _handle_save(self) -> None:
        text = self.ui.inpClassName.text().strip()
        if not text:
            return

        selected_items = self.ui.lstClasses.selectedItems()

        if selected_items:

            item = selected_items[0]
            old_name = item.text()

            if text == old_name:
                return

            print(f"[ClassManager] Renaming class '{old_name}' to '{text}'...")
            index = next(
                (i for i, x in enumerate(self.cached_classes) if x.name == old_name),
                None,
            )
            if index is not None:
                old_class = self.cached_classes[index]
                new_class = ObjectClass(name=text)

                self.network_service.request_db_rename_class(old_class, new_class)

        else:
            print(f"[ClassManager] Adding new class '{text}'...")

            is_repeat = any(x.name == text for x in self.cached_classes)

            if is_repeat:
                # TODO - Додати переклад
                QMessageBox.critical(self, "Увага", "Клас з такою назвою вже існує.")
                return

            new_class = ObjectClass(name=text)
            self.network_service.request_db_add_class(new_class)

    def _delete_class(self) -> None:
        item = self.ui.lstClasses.currentItem()
        if not item:
            # TODO - Додати переклад
            QMessageBox.warning(self, "Увага", "Виберіть клас для видалення.")
            return

        class_name = item.text()
        class_id_data = item.data(Qt.ItemDataRole.UserRole)
        class_id = int(class_id_data) if class_id_data is not None else -1

        # TODO - Додати переклад
        res = QMessageBox.question(
            self,
            "Видалення",
            f"Видалити клас '{class_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if res == QMessageBox.StandardButton.Yes:
            print(f"[ClassManager] Deleting class '{class_name}' (ID: {class_id})...")

            self.network_service.request_db_delete_class(class_id)

    def add_cache_class(self, class_obj: ObjectClass):
        self.cached_classes.append(class_obj)
        self._populate_list()

    def update_cache_class(self, new_class_obj: ObjectClass):
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

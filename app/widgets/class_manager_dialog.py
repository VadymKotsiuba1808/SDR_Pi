from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QListWidgetItem,
    QMessageBox,
    QWidget,
)
from PyQt6 import uic
from PyQt6.QtCore import Qt, QEvent, QTranslator, QCoreApplication

from app.ui.ui_class_manager_dialog import Ui_ClassManagerDialog
from app.widgets.keyboard_widget import KeyboardWidget
from app.services.keyboard_service import KeyboardService
from app.services.database_service import DatabaseService
from app.protocols import ObjectManagerDialogSettings


class ClassManagerDialog(QDialog):
    def __init__(
        self,
        db_service: DatabaseService,
        settings_service: ObjectManagerDialogSettings,
        keyboard_service: KeyboardService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.db_service = db_service
        self.settings_service = settings_service
        self.keyboard_service = keyboard_service

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()
        self._load_language()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if self.settings_service.compiled_ui_using_enabled:
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

    def _adjust_fields(self) -> None:
        self.ui.keyboardLayout.addWidget(self.lang_widget)
        self._refresh_list()

    def _connect_handlers(self) -> None:
        self.ui.btnAdd.clicked.connect(self._handle_save)
        self.ui.btnDelete.clicked.connect(self._delete_class)
        self.ui.btnClose.clicked.connect(self.accept)
        self.ui.lstClasses.itemClicked.connect(self._on_item_clicked)

        if hasattr(self.ui, "btnClearSelection"):
            self.ui.btnClearSelection.clicked.connect(self._clear_selection)

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return
        QCoreApplication.removeTranslator(self.translator)

    def _refresh_list(self) -> None:
        self.ui.lstClasses.clear()
        classes = self.db_service.get_all_classes()

        print(f"[ClassManager] Loaded {len(classes)} classes.")

        for c in classes:
            item = QListWidgetItem(c.name)
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self.ui.lstClasses.addItem(item)

        self._clear_selection()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.ui.inpClassName.setText(item.text())
        self.ui.btnAdd.setText("Зберегти")

    def _clear_selection(self) -> None:
        self.ui.lstClasses.clearSelection()
        self.ui.inpClassName.clear()
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

            if self.db_service.rename_class(old_name, text):
                self._refresh_list()
            else:
                print(f"[ClassManager] Error: Failed to rename '{old_name}'.")
                QMessageBox.warning(self, "Помилка", "Помилка перейменування.")
        else:
            print(f"[ClassManager] Adding new class '{text}'...")

            if self.db_service.add_class(text):
                self._refresh_list()
            else:
                print(f"[ClassManager] Error: Failed to add '{text}'.")
                QMessageBox.warning(self, "Помилка", "Такий клас вже існує.")

    def _delete_class(self) -> None:
        item = self.ui.lstClasses.currentItem()
        if not item:
            QMessageBox.warning(self, "Увага", "Виберіть клас для видалення.")
            return

        class_name = item.text()
        class_id_data = item.data(Qt.ItemDataRole.UserRole)
        class_id = int(class_id_data) if class_id_data is not None else -1

        if self.db_service.is_class_used(class_id):
            print(
                f"[ClassManager] Blocked deletion: Class '{class_name}' (ID: {class_id}) is in use."
            )
            QMessageBox.critical(
                self,
                "Неможливо видалити",
                f"Клас '{class_name}' використовується одним або кількома об'єктами.\n"
                "Спочатку видаліть або змініть об'єкти цього класу.",
            )
            return

        res = QMessageBox.question(
            self,
            "Видалення",
            f"Видалити клас '{class_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if res == QMessageBox.StandardButton.Yes:
            print(f"[ClassManager] Deleting class '{class_name}' (ID: {class_id})...")

            self.db_service.delete_class(class_id)
            self._refresh_list()

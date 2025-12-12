"""
Діалогове вікно керування об'єктами (Object Manager).
"""

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QMessageBox, QHeaderView
from PyQt6.QtCore import Qt, QEvent, QCoreApplication

from app.protocols import ObjectManagerDialogSettings
from app.widgets.object_editor_dialog import ObjectEditorDialog
from app.services.database_service import DatabaseService
from app.models.detection_object import DetectionObject
from app.ui.ui_object_manager_dialog import Ui_ObjectManager
from app.utils.ui_utils import move_dialog_down


class ObjectManagerDialog(QDialog):
    PAGE_SIZE = 15

    def __init__(
        self,
        db_service: DatabaseService,
        settings_service: ObjectManagerDialogSettings,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.db_service = db_service
        self.settings_service = settings_service
        self.cached_objects: list[DetectionObject] = []

        self.current_page = 1
        self.total_pages = 1

        self._load_ui()
        self._init_table()
        self._connect_handlers()

        self.refresh_data()

        self._load_language()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_ObjectManager()
            self.ui.setupUi(self)
        else:
            ui_path = "app/ui/object_manager_dialog.ui"

            uic.loadUi(ui_path, self)
            self.ui = self

    def _init_table(self):
        header = self.ui.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.tableWidget.setColumnWidth(1, 100)
        self.ui.tableWidget.setColumnWidth(2, 100)
        self.ui.tableWidget.setColumnWidth(3, 150)
        self.ui.tableWidget.setColumnWidth(4, 150)

    def _connect_handlers(self):
        self.ui.btnRefresh.clicked.connect(self.refresh_data)
        self.ui.btnAdd.clicked.connect(self._open_add_dialog)
        self.ui.btnEdit.clicked.connect(self._open_edit_dialog)
        self.ui.btnDelete.clicked.connect(self._handle_delete)
        self.ui.btnClose.clicked.connect(self.reject)
        self.ui.tableWidget.doubleClicked.connect(self._open_edit_dialog)

        self.ui.btnPrevPage.clicked.connect(self._prev_page)
        self.ui.btnNextPage.clicked.connect(self._next_page)

        self.db_service.objects_page_loaded.connect(self._populate_table)
        self.db_service.operation_status.connect(self._handle_db_status)

    def refresh_data(self):
        self.db_service.request_objects_page(self.current_page, self.PAGE_SIZE)

    def _load_language(self):
        lang_code = self.settings_service.lang_code

        if lang_code == None:
            return

        QCoreApplication.removeTranslator(self.translator)

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_data()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_data()

    def _handle_db_status(self, op_type, success, msg):
        if success:
            self.refresh_data()

    def _populate_table(self, objects_list, current_page, total_pages):
        """Оновлює таблицю даними з новою структурою RF (min/max)."""
        self.cached_objects = objects_list
        self.current_page = current_page
        self.total_pages = total_pages

        self.ui.lblPageInfo.setText(f"Сторінка {current_page} з {total_pages}")
        self.ui.btnPrevPage.setEnabled(current_page > 1)
        self.ui.btnNextPage.setEnabled(current_page < total_pages)

        self.ui.tableWidget.setRowCount(0)

        for obj in objects_list:
            row_idx = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(row_idx)

            # Назва
            name_item = QTableWidgetItem(obj.get("name", "Unnamed"))
            name_item.setData(Qt.ItemDataRole.UserRole, obj.get("id"))
            self.ui.tableWidget.setItem(row_idx, 0, name_item)

            # Клас
            self.ui.tableWidget.setItem(
                row_idx, 1, QTableWidgetItem(obj.get("object_class", ""))
            )

            # Небезпека
            is_dang = obj.get("is_dangerous", False)
            dang_item = QTableWidgetItem("ТАК" if is_dang else "Ні")
            if is_dang:
                dang_item.setForeground(Qt.GlobalColor.red)
            self.ui.tableWidget.setItem(row_idx, 2, dang_item)

            # --- RF (Радіо) ---
            rf_list = obj.get("rf_params", [])
            rf_str = "-"
            if rf_list and isinstance(rf_list, list):
                if len(rf_list) == 1:
                    val = rf_list[0]
                    f_min = val.get("min_mhz", 0)
                    f_max = val.get("max_mhz", 0)
                    if f_min == f_max:
                        rf_str = f"{f_min} MHz"
                    else:
                        rf_str = f"{f_min}-{f_max} MHz"
                else:
                    rf_str = f"{len(rf_list)} freq(s)"

            self.ui.tableWidget.setItem(row_idx, 3, QTableWidgetItem(rf_str))

            snd_list = obj.get("sound_params", [])
            snd_str = "-"
            if snd_list and isinstance(snd_list, list):
                if len(snd_list) > 3:
                    snd_str = f"{len(snd_list)} items"
                else:
                    snd_str = ", ".join(map(str, snd_list)) + " Hz"

            self.ui.tableWidget.setItem(row_idx, 4, QTableWidgetItem(snd_str))

    def _get_selected_id(self):
        selected_items = self.ui.tableWidget.selectedItems()
        if not selected_items:
            return None
        row = selected_items[0].row()
        item = self.ui.tableWidget.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole)

    def _open_add_dialog(self):
        dialog = ObjectEditorDialog(self.db_service, self.settings_service, self)
        move_dialog_down(dialog, self.geometry())
        dialog.exec()

    def _open_edit_dialog(self):
        obj_id = self._get_selected_id()
        if not obj_id:
            QMessageBox.warning(self, "Увага", "Виберіть об'єкт для редагування.")
            return

        target_obj = next((o for o in self.cached_objects if o["id"] == obj_id), None)

        if target_obj:
            dialog = ObjectEditorDialog(
                self.db_service, self.settings_service, self, object_data=target_obj
            )
            move_dialog_down(dialog, self.geometry(), -50)
            dialog.exec()

    def _handle_delete(self):
        obj_id = self._get_selected_id()
        if not obj_id:
            QMessageBox.warning(self, "Увага", "Виберіть об'єкт для видалення.")
            return

        confirm = QMessageBox.question(
            self,
            "Видалення",
            "Ви впевнені, що хочете видалити цей запис?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self.db_service.delete_object(obj_id)

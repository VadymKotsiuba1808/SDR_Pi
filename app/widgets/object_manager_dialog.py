import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QMessageBox, QHeaderView
from PyQt6.QtCore import Qt, QEvent

from app.widgets.object_editor_dialog import ObjectEditorDialog

from app.ui.ui_object_manager_dialog import Ui_ObjectManager


class ObjectManagerDialog(QDialog):
    PAGE_SIZE = 15

    def __init__(self, db_service, settings_service, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self.settings_service = settings_service
        self.cached_objects = []

        self.current_page = 1
        self.total_pages = 1

        self._load_ui()
        self._init_table()
        self._connect_signals()

        self.refresh_data()

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
            ui_path = os.path.join(
                os.path.dirname(__file__), "../ui/object_manager_dialog.ui"
            )
            uic.loadUi(ui_path, self)
            self.ui = self

    def _init_table(self):
        header = self.ui.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.tableWidget.setColumnWidth(1, 100)
        self.ui.tableWidget.setColumnWidth(2, 100)
        self.ui.tableWidget.setColumnWidth(3, 150)
        self.ui.tableWidget.setColumnWidth(4, 150)

    def _connect_signals(self):
        self.ui.btnRefresh.clicked.connect(self.refresh_data)
        self.ui.btnAdd.clicked.connect(self._open_add_dialog)
        self.ui.btnEdit.clicked.connect(self._open_edit_dialog)
        self.ui.btnDelete.clicked.connect(self._handle_delete)
        self.ui.tableWidget.doubleClicked.connect(self._open_edit_dialog)

        self.ui.btnPrevPage.clicked.connect(self._prev_page)
        self.ui.btnNextPage.clicked.connect(self._next_page)

        self.db_service.objects_page_loaded.connect(self._populate_table)
        self.db_service.operation_status.connect(self._handle_db_status)

    def refresh_data(self):
        """Запитує поточну сторінку."""
        self.db_service.request_objects_page(self.current_page, self.PAGE_SIZE)

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
        """Оновлює таблицю та стан кнопок."""
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

            name_item = QTableWidgetItem(obj.get("name", "Unnamed"))
            name_item.setData(Qt.ItemDataRole.UserRole, obj.get("id"))
            self.ui.tableWidget.setItem(row_idx, 0, name_item)

            self.ui.tableWidget.setItem(
                row_idx, 1, QTableWidgetItem(obj.get("object_class", ""))
            )

            is_dang = obj.get("is_dangerous", False)
            dang_item = QTableWidgetItem("ТАК" if is_dang else "Ні")
            if is_dang:
                dang_item.setForeground(Qt.GlobalColor.red)
            self.ui.tableWidget.setItem(row_idx, 2, dang_item)

            rf = obj.get("rf_params")
            rf_str = f"{rf['freq_mhz']} MHz" if rf else "-"
            self.ui.tableWidget.setItem(row_idx, 3, QTableWidgetItem(rf_str))

            aud = obj.get("audio_params")
            aud_str = f"{aud['min_freq']}-{aud['max_freq']} Hz" if aud else "-"
            self.ui.tableWidget.setItem(row_idx, 4, QTableWidgetItem(aud_str))

    def _get_selected_id(self):
        """Повертає ID вибраного рядка або None."""
        selected_items = self.ui.tableWidget.selectedItems()
        if not selected_items:
            return None

        row = selected_items[0].row()
        item = self.ui.tableWidget.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole)

    def _open_add_dialog(self):
        dialog = ObjectEditorDialog(self.db_service, self.settings_service, self)
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

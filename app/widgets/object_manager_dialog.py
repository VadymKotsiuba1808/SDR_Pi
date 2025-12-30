from typing import Optional, List
import math

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QDialog,
    QTableWidgetItem,
    QMessageBox,
    QHeaderView,
    QWidget,
)
from PyQt6.QtCore import Qt, QEvent, QCoreApplication, QTranslator

from app.protocols import ObjectManagerDialogSettings
from app.widgets.object_editor_dialog import ObjectEditorDialog
from app.widgets.class_manager_dialog import ClassManagerDialog
from app.services.database_service import DatabaseService
from app.services.keyboard_service import KeyboardService
from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.ui.ui_object_manager_dialog import Ui_ObjectManager
from app.utils.ui_utils import move_dialog_down


class ObjectManagerDialog(QDialog):
    """
    Діалогове вікно керування об'єктами (Object Manager).
    """

    PAGE_SIZE = 15
    PRELOAD_PAGES_COUNT = 6

    def __init__(
        self,
        db_service: DatabaseService,
        settings_service: ObjectManagerDialogSettings,
        keyboard: KeyboardService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.db_service = db_service
        self.settings_service = settings_service
        self.keyboard_service = keyboard

        self._load_ui()
        self._setup_state_variables()
        self._init_table()
        self._connect_handlers()

        self.refresh_data()
        self._load_language()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_ObjectManager()
            self.ui.setupUi(self)
        else:
            ui_path = "app/ui/object_manager_dialog.ui"
            uic.loadUi(ui_path, self)
            self.ui = self

    def _setup_state_variables(self) -> None:
        self.cached_objects: List[DetectionObject] = []
        self.current_page: int = 1
        self.current_load: int = 0
        self.total_pages: int = 1
        self.total_items: int = 0
        self.translator = QTranslator()

    def _init_table(self) -> None:
        header = self.ui.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.tableWidget.setColumnWidth(1, 100)
        self.ui.tableWidget.setColumnWidth(2, 100)
        self.ui.tableWidget.setColumnWidth(3, 150)
        self.ui.tableWidget.setColumnWidth(4, 150)

    def _connect_handlers(self) -> None:
        self.ui.btnRefresh.clicked.connect(self.refresh_data)

        self.ui.btnManageClasses.clicked.connect(self._open_class_manager)

        self.ui.btnAdd.clicked.connect(self._open_add_dialog)
        self.ui.btnEdit.clicked.connect(self._open_edit_dialog)
        self.ui.btnDelete.clicked.connect(self._handle_delete)
        self.ui.btnClose.clicked.connect(self.reject)

        self.ui.tableWidget.doubleClicked.connect(self._open_edit_dialog)

        self.ui.btnPrevPage.clicked.connect(self._prev_page)
        self.ui.btnNextPage.clicked.connect(self._next_page)

        self.db_service.objects_page_loaded.connect(self._populate_table_from_db)
        self.db_service.operation_status.connect(self._handle_db_status)

    def refresh_data(self) -> None:
        last_page_in_cache = self.current_load * self.PRELOAD_PAGES_COUNT
        first_page_in_cache = last_page_in_cache - self.PRELOAD_PAGES_COUNT + 1

        if (
            first_page_in_cache <= self.current_page <= last_page_in_cache
            and self.cached_objects
        ):
            print(
                f"[ObjectManager] Page {self.current_page} found in cache. Rendering..."
            )
            start_index = self._calculate_start_index()
            if start_index < 0:
                start_index = 0

            current_list = self.cached_objects[
                start_index : start_index + self.PAGE_SIZE
            ]
            self._populate_table(current_list)
        else:
            self.current_load = math.ceil(self.current_page / self.PRELOAD_PAGES_COUNT)
            if self.current_load < 1:
                self.current_load = 1
            limit = self.PAGE_SIZE * self.PRELOAD_PAGES_COUNT

            print(
                f"[ObjectManager] Requesting DB Chunk #{self.current_load} (Limit: {limit})..."
            )
            self.db_service.request_objects_page(self.current_load, limit)

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return
        QCoreApplication.removeTranslator(self.translator)

    def _calculate_start_index(self) -> int:
        global_start = (self.current_page - 1) * self.PAGE_SIZE
        chunk_start = (
            (self.current_load - 1) * self.PAGE_SIZE * self.PRELOAD_PAGES_COUNT
        )
        return global_start - chunk_start

    def _prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_data()

    def _next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_data()

    def _handle_db_status(self, op_type: str, success: bool, msg: str) -> None:
        print(
            f"[ObjectManager] DB Operation '{op_type}': Success={success}, Msg='{msg}'"
        )
        if success:
            self.refresh_data()

    def _populate_table_from_db(
        self,
        objects_list: List[DetectionObject],
        current_load_chunk: int,
        total_items: int,
    ) -> None:
        print(
            f"[ObjectManager] Data received. Chunk: {current_load_chunk}, Total Items: {total_items}"
        )
        self.cached_objects = objects_list
        self.current_load = current_load_chunk
        self.total_pages = math.ceil(total_items / self.PAGE_SIZE)

        start_index = self._calculate_start_index()
        current_list = objects_list[start_index : start_index + self.PAGE_SIZE]
        self._populate_table(current_list)

    def _populate_table(self, objects_list: List[DetectionObject]) -> None:
        self.ui.lblPageInfo.setText(
            f"Сторінка {self.current_page} з {self.total_pages}"
        )
        self.ui.btnPrevPage.setEnabled(self.current_page > 1)
        self.ui.btnNextPage.setEnabled(self.current_page < self.total_pages)

        self.ui.tableWidget.setRowCount(0)

        for obj in objects_list:
            row_idx = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(row_idx)

            # Назва
            name_item = QTableWidgetItem(obj.name)
            name_item.setData(Qt.ItemDataRole.UserRole, obj.id)  # ID типу int
            self.ui.tableWidget.setItem(row_idx, 0, name_item)

            # Клас
            self.ui.tableWidget.setItem(row_idx, 1, QTableWidgetItem(obj.object_class))

            # Небезпека
            is_dang = obj.is_dangerous
            dang_item = QTableWidgetItem("ТАК" if is_dang else "Ні")
            if is_dang:
                dang_item.setForeground(Qt.GlobalColor.red)
            self.ui.tableWidget.setItem(row_idx, 2, dang_item)

            # --- RF (Радіо) ---
            rf_list = obj.rf_params
            rf_str = "-"
            if rf_list:
                if len(rf_list) == 1:
                    rf_str = f"{rf_list[0]} MHz"
                else:
                    rf_str = f"{len(rf_list)} freq(s)"

            self.ui.tableWidget.setItem(row_idx, 3, QTableWidgetItem(rf_str))

            # --- Sound ---
            snd_list = obj.sound_params
            snd_str = "-"
            if snd_list:
                if len(snd_list) > 3:
                    snd_str = f"{len(snd_list)} items"
                else:
                    snd_str = ", ".join(map(str, snd_list)) + " Hz"

            self.ui.tableWidget.setItem(row_idx, 4, QTableWidgetItem(snd_str))

    def _get_selected_id(self) -> Optional[int]:
        selected_items = self.ui.tableWidget.selectedItems()
        if not selected_items:
            return None
        row = selected_items[0].row()
        item = self.ui.tableWidget.item(row, 0)
        val = item.data(Qt.ItemDataRole.UserRole)
        return int(val) if val is not None else None

    def _open_class_manager(self) -> None:
        dialog = ClassManagerDialog(
            self.db_service, self.settings_service, self.keyboard_service, parent=self
        )
        move_dialog_down(dialog, self.geometry(), 0)
        dialog.exec()

        print("[ObjectManager] Class manager closed. Refreshing data...")
        self.cached_objects = []
        self.refresh_data()

    def _open_editor(self, obj_data: Optional[DetectionObject]) -> None:
        classes_list: List[ObjectClass] = self.db_service.get_all_classes()

        dialog = ObjectEditorDialog(
            settings_service=self.settings_service,
            keyboard=self.keyboard_service,
            known_classes=classes_list,
            parent=self,
            object_data=obj_data,
        )
        move_dialog_down(dialog, self.geometry(), -90)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_object = dialog.get_new_object()
            if new_object:
                if obj_data:
                    self.db_service.update_object(new_object.to_dict())
                else:
                    self.db_service.add_object(new_object.to_dict())

            self.cached_objects = []
            if not obj_data:
                self.current_load = 1
                self.current_page = 1
            self.refresh_data()

    def _handle_class_management_from_editor(
        self, editor_dialog: ObjectEditorDialog
    ) -> None:
        manager = ClassManagerDialog(
            self.db_service,
            self.settings_service,
            self.keyboard_service,
            parent=editor_dialog,
        )
        move_dialog_down(manager, editor_dialog.geometry(), 0)
        manager.exec()

        new_classes = self.db_service.get_all_classes()
        editor_dialog.update_classes_list(new_classes)

    def _open_add_dialog(self) -> None:
        self._open_editor(None)

    def _open_edit_dialog(self) -> None:
        obj_id = self._get_selected_id()
        if not obj_id:
            QMessageBox.warning(self, "Увага", "Виберіть об'єкт для редагування.")
            return

        target_obj = next((o for o in self.cached_objects if o.id == obj_id), None)

        if not target_obj:
            return

        self._open_editor(target_obj)

    def _handle_delete(self) -> None:
        obj_id = self._get_selected_id()
        if not obj_id:
            QMessageBox.warning(self, "Увага", "Виберіть об'єкт для видалення.")
            return

        confirm = QMessageBox.question(
            self,
            "Видалення",
            "Видалити цей запис?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db_service.delete_object(obj_id)
            self.cached_objects = []

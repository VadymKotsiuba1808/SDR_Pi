import math
from typing import List, Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTranslator
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
    QWidget,
)

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED, RF_PARAMS__DIVIDER
from app.core.mixins import TestUIOptimizationMixin
from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, ServiceResponse
from app.protocols import LangSettings
from app.services.keyboard_service import KeyboardService
from app.services.pi_network_service import PiNetworkService
from app.ui.ui_object_manager_dialog import Ui_ObjectManager
from app.utils.convert_measurement_unit import convert_hz_to_mhz
from app.utils.ui_utils import move_dialog_down
from app.widgets.class_manager_dialog import ClassManagerDialog
from app.widgets.object_editor_dialog import ObjectEditorDialog

ALLOW_DB_OPERATIONS = [
    DbOperation.ADD_OBJECT,
    DbOperation.UPDATE_OBJECT,
    DbOperation.DELETE_OBJECT,
    DbOperation.GET_OBJECTS_PAGE,
    DbOperation.GET_CLASSES,
]


class ObjectManagerDialog(QDialog, TestUIOptimizationMixin):
    """
    Діалогове вікно керування об'єктами (База даних сигнатур).

    Дозволяє оператору переглядати, додавати, редагувати та видаляти
    інформацію про типи БПЛА та їх радіочастотні/акустичні сигнатури.
    Використовує механізм сторінкової пагінації та кешування для
    оптимізації роботи з великою базою даних через мережу.
    """

    PAGE_SIZE = 15  # Кількість об'єктів на одній сторінці UI
    PRELOAD_PAGES_COUNT = 6  # Скільки сторінок завантажувати за один мережевий запит

    def __init__(
        self,
        network_service: PiNetworkService,
        settings_service: LangSettings,
        keyboard: KeyboardService,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Ініціалізує менеджер об'єктів.

        Args:
            network_service (PiNetworkService): Сервіс для зв'язку з БД сервера.
            settings_service (LangSettings): Налаштування мови та інтерфейсу.
            keyboard (KeyboardService): Сервіс для роботи з віртуальною клавіатурою.
            parent (Optional[QWidget]): Батьківське вікно.
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.network_service = network_service
        self.settings_service = settings_service
        self.keyboard_service = keyboard

        self._load_ui()
        self._setup_state_variables()
        self._init_table()
        self._connect_handlers()

        # Первинне завантаження даних
        self.refresh_data()
        self._load_language()
        self.apply_test_ui_optimization()

    def changeEvent(self, a0: QEvent | None) -> None:
        """Обробник зміни системних параметрів (мова)."""
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        """Завантажує UI компоненти менеджеру."""
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_ObjectManager()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/object_manager_dialog.ui", self)
            self.ui = cast(Ui_ObjectManager, self)

    def _setup_state_variables(self) -> None:
        """Ініціалізує внутрішні змінні для кешування та пагінації."""
        self.cached_objects: List[DetectionObject] = []
        self.current_page: int = 1
        self.current_load: int = (
            0  # Індекс поточного завантаженого чанку (порції сторінок)
        )
        self.total_pages: int = 1
        self.total_items: int = 0
        self.translator = QTranslator()
        self._waiting_classes_for_editor = False

        self.edit_obj: Optional[DetectionObject] = None

    def _init_table(self) -> None:
        """Налаштовує параметри таблиці відображення об'єктів."""
        header = self.ui.tableWidget.horizontalHeader()
        if header is not None:
            # Розтягуємо першу колонку (Назва) на весь доступний простір
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        # Фіксована ширина для допоміжних колонок
        self.ui.tableWidget.setColumnWidth(1, 100)  # Клас
        self.ui.tableWidget.setColumnWidth(2, 100)  # Небезпека
        self.ui.tableWidget.setColumnWidth(3, 150)  # RF параметри
        self.ui.tableWidget.setColumnWidth(4, 150)  # Sound параметри

    def _connect_handlers(self) -> None:
        """Підключає сигнали кнопок та мережеві відповіді."""
        self.ui.btnRefresh.clicked.connect(self._force_refresh)
        self.ui.btnManageClasses.clicked.connect(self._open_class_manager)

        self.ui.btnAdd.clicked.connect(self._open_add_dialog)
        self.ui.btnEdit.clicked.connect(self._open_edit_dialog)
        self.ui.btnDelete.clicked.connect(self._handle_delete)
        self.ui.btnClose.clicked.connect(self.reject)

        # Подвійний клік по рядку відкриває редагування
        self.ui.tableWidget.doubleClicked.connect(self._open_edit_dialog)

        # Навігація по сторінках
        self.ui.btnPrevPage.clicked.connect(self._prev_page)
        self.ui.btnNextPage.clicked.connect(self._next_page)

        self.network_service.request_finished.connect(self._handle_db_status)

    def refresh_data(self) -> None:
        """
        Оновлює вміст таблиці.

        Перевіряє, чи є потрібна сторінка в локальному кеші. Якщо ні —
        надсилає запит на сервер для завантаження нового чанку даних.
        """
        last_page_in_cache = self.current_load * self.PRELOAD_PAGES_COUNT
        first_page_in_cache = last_page_in_cache - self.PRELOAD_PAGES_COUNT + 1

        # Перевірка наявності сторінки в поточному чанку кешу
        if (
            first_page_in_cache <= self.current_page <= last_page_in_cache
            and self.cached_objects
        ):
            print(f"[ObjectManager] Page {self.current_page} found in cache.")
            start_index = self._calculate_start_index()
            if start_index < 0:
                start_index = 0

            current_list = self.cached_objects[
                start_index : start_index + self.PAGE_SIZE
            ]
            self._populate_table(current_list)
        else:
            # Розрахунок, який чанк (групу сторінок) потрібно завантажити
            self.current_load = math.ceil(self.current_page / self.PRELOAD_PAGES_COUNT)
            if self.current_load < 1:
                self.current_load = 1
            limit = self.PAGE_SIZE * self.PRELOAD_PAGES_COUNT

            print(f"[ObjectManager] Requesting DB Chunk #{self.current_load}...")
            self.network_service.request_db_objects_page(self.current_load, limit)

    def _load_language(self) -> None:
        """Завантажує переклад (заглушка, оскільки UI використовує tr())."""
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return
        QCoreApplication.removeTranslator(self.translator)

    def _force_refresh(self) -> None:
        """Очищує кеш та примусово перевантажує дані з сервера."""
        self.cached_objects = []
        self.refresh_data()

    def _calculate_start_index(self) -> int:
        """Обчислює зсув (offset) всередині завантаженого чанку об'єктів для поточної сторінки."""
        global_start = (self.current_page - 1) * self.PAGE_SIZE
        chunk_start = (
            (self.current_load - 1) * self.PAGE_SIZE * self.PRELOAD_PAGES_COUNT
        )
        return global_start - chunk_start

    def _prev_page(self) -> None:
        """Перехід на попередню сторінку."""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_data()

    def _next_page(self) -> None:
        """Перехід на наступну сторінку."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_data()

    def _handle_db_status(self, response: ServiceResponse) -> None:
        """
        Централізований обробник відповідей від бази даних.

        Опрацьовує результати додавання, редагування, видалення та пагінації.
        Також відповідає за відкриття редактора після успішного завантаження класів.
        """
        if response.operation not in ALLOW_DB_OPERATIONS:
            return

        if response.is_error:
            if response.operation == DbOperation.GET_CLASSES:
                self._waiting_classes_for_editor = False
            QMessageBox.critical(
                self, response.get_title(), response.get_message_or_default()
            )
            return

        match response.operation:
            case DbOperation.ADD_OBJECT:
                if response.data:
                    self.add_cache_obj(DetectionObject.from_dict(response.data))
            case DbOperation.UPDATE_OBJECT:
                if response.data:
                    self.update_cache_obj(DetectionObject.from_dict(response.data))
            case DbOperation.DELETE_OBJECT:
                if isinstance(response.data, dict):
                    obj_id = response.data.get("id")
                    if obj_id:
                        self.delete_cache_obj(obj_id)
            case DbOperation.GET_OBJECTS_PAGE:
                if isinstance(response.data, dict):
                    items = response.data.get("items", [])
                    page = response.data.get("page", 1)
                    total = response.data.get("total", 0)
                    obj_list = [DetectionObject.from_dict(item) for item in items]
                    self._populate_table_from_db(obj_list, page, total)
            case DbOperation.GET_CLASSES:
                if isinstance(response.data, dict):
                    classes_raw = response.data.get("classes", [])
                    classes_list = [ObjectClass.from_dict(c) for c in classes_raw]
                    # Якщо ми чекали на класи для відкриття редактора об'єкта
                    if self._waiting_classes_for_editor:
                        self._waiting_classes_for_editor = False
                        self._open_editor(classes_list)

    def _populate_table_from_db(
        self,
        objects_list: List[DetectionObject],
        current_load_chunk: int,
        total_items: int,
    ) -> None:
        """Оновлює внутрішній стан після отримання нового чанку даних з мережі."""
        self.cached_objects = objects_list
        self.current_load = current_load_chunk
        self.total_pages = math.ceil(total_items / self.PAGE_SIZE)

        start_index = self._calculate_start_index()
        current_list = objects_list[start_index : start_index + self.PAGE_SIZE]
        self._populate_table(current_list)

    def _populate_table(self, objects_list: List[DetectionObject]) -> None:
        """Перемальовує рядки таблиці на основі наданого списку об'єктів."""
        self.ui.lblPageInfo.setText(
            self.tr("Page {} of {}").format(self.current_page, self.total_pages)
        )
        self.ui.btnPrevPage.setEnabled(self.current_page > 1)
        self.ui.btnNextPage.setEnabled(self.current_page < self.total_pages)

        self.ui.tableWidget.setRowCount(0)
        for obj in objects_list:
            row_idx = self.ui.tableWidget.rowCount()
            self._set_object_row(obj, row_idx)

    def _set_object_row(self, obj: DetectionObject, row_idx: int) -> None:
        """Створює та заповнює елементами один рядок таблиці."""
        if row_idx >= self.ui.tableWidget.rowCount():
            self.ui.tableWidget.insertRow(row_idx)

        # Колонки: Назва (з прихованим ID), Клас, Небезпека, RF, Sound
        name_item = QTableWidgetItem(obj.name)
        name_item.setData(Qt.ItemDataRole.UserRole, obj.id)
        self.ui.tableWidget.setItem(row_idx, 0, name_item)
        self.ui.tableWidget.setItem(row_idx, 1, QTableWidgetItem(obj.object_class))

        is_dang = obj.is_dangerous
        dang_item = QTableWidgetItem(self.tr("YES") if is_dang else self.tr("NO"))
        if is_dang:
            dang_item.setForeground(Qt.GlobalColor.red)
        self.ui.tableWidget.setItem(row_idx, 2, dang_item)

        # Форматування RF параметрів (діапазон частот)
        rf_str = "-"
        if obj.rf_params_hz:
            if len(obj.rf_params_hz) == 1:
                parts = obj.rf_params_hz[0].split(RF_PARAMS__DIVIDER)
                min_f = round(convert_hz_to_mhz(float(parts[0])), 1)
                max_f = round(convert_hz_to_mhz(float(parts[1])), 1)
                rf_str = self.tr("{}-{} MHz").format(min_f, max_f)
            else:
                rf_str = self.tr("{} freq(s)").format(len(obj.rf_params_hz))
        self.ui.tableWidget.setItem(row_idx, 3, QTableWidgetItem(rf_str))

        # Форматування параметрів звуку
        snd_str = "-"
        if obj.sound_params_hz:
            if len(obj.sound_params_hz) > 3:
                snd_str = self.tr("{} items").format(len(obj.sound_params_hz))
            else:
                snd_str = ", ".join(map(str, obj.sound_params_hz)) + self.tr(" Hz")
        self.ui.tableWidget.setItem(row_idx, 4, QTableWidgetItem(snd_str))

    def _get_selected_id(self) -> Optional[int]:
        """Повертає унікальний ID виділеного у таблиці об'єкта."""
        selected_items = self.ui.tableWidget.selectedItems()
        if not selected_items:
            return None
        row = selected_items[0].row()
        item = self.ui.tableWidget.item(row, 0)
        if item is None:
            return None
        val = item.data(Qt.ItemDataRole.UserRole)
        return int(val) if val is not None else None

    def _open_class_manager(self) -> None:
        """Відкриває діалог керування класами (категоріями) об'єктів."""
        dialog = ClassManagerDialog(
            self.network_service,
            self.settings_service,
            self.keyboard_service,
            parent=self,
        )
        move_dialog_down(dialog, self.geometry(), 0)
        dialog.exec()
        # Повне оновлення після редагування класів, оскільки вони впливають на відображення
        self._force_refresh()

    def _open_editor(self, classes_list: List[ObjectClass]) -> None:
        """Відкриває вікно редагування або створення об'єкта."""
        dialog = ObjectEditorDialog(
            settings_service=self.settings_service,
            keyboard=self.keyboard_service,
            known_classes=classes_list,
            parent=self,
            object_data=self.edit_obj,
        )
        move_dialog_down(dialog, self.geometry(), -70)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_object = dialog.get_new_object()
            if new_object:
                if self.edit_obj:
                    new_object.id = self.edit_obj.id
                    self.network_service.request_db_update_object(new_object)
                else:
                    self.network_service.request_db_add_object(new_object)

    def _open_add_dialog(self) -> None:
        """Ініціює процес додавання нового об'єкта."""
        self.edit_obj = None
        self._waiting_classes_for_editor = True
        self.network_service.request_db_classes()

    def _open_edit_dialog(self) -> None:
        """Ініціює процес редагування вибраного об'єкта."""
        obj_id = self._get_selected_id()
        if not obj_id:
            QMessageBox.warning(
                self, self.tr("Warning"), self.tr("Select a object to edit.")
            )
            return

        target_obj = next((o for o in self.cached_objects if o.id == obj_id), None)
        if not target_obj:
            return

        self.edit_obj = target_obj
        self._waiting_classes_for_editor = True
        self.network_service.request_db_classes()

    def _handle_delete(self) -> None:
        """Обробляє запит на видалення об'єкта з підтвердженням користувача."""
        obj_id = self._get_selected_id()
        if not obj_id:
            QMessageBox.warning(
                self, self.tr("Warning"), self.tr("Select a object to delete.")
            )
            return

        confirm = QMessageBox.question(
            self,
            self.tr("Delete"),
            self.tr("Delete this item?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.network_service.request_db_delete_object(obj_id)

    def add_cache_obj(self, obj: DetectionObject) -> None:
        """Додає об'єкт у початок локального кешу."""
        self.cached_objects.insert(0, obj)
        self.refresh_data()

    def update_cache_obj(self, new_obj: DetectionObject) -> None:
        """Оновлює дані об'єкта в локальному кеші."""
        index = next(
            (i for i, x in enumerate(self.cached_objects) if x.id == new_obj.id), None
        )
        if index is not None:
            self.cached_objects[index] = new_obj
            self.refresh_data()

    def delete_cache_obj(self, obj_id: int) -> None:
        """Видаляє об'єкт з локального кешу за ID."""
        index = next(
            (i for i, x in enumerate(self.cached_objects) if x.id == obj_id), None
        )
        if index is not None:
            self.cached_objects.pop(index)
            self.refresh_data()

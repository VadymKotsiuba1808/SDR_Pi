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
        """
        Ініціалізує діалогове вікно керування класами.

        Args:
            network_service: Сервіс мережевої взаємодії.
            settings_service: Сервіс налаштувань мови.
            keyboard_service: Сервіс керування клавіатурою.
            parent: Батьківський віджет.
        """
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
        """
        Обробляє події зміни стану вікна, зокрема зміну мови.

        Args:
            a0: Подія, що відбулася.
        """
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        """
        Завантажує інтерфейс користувача.

        Використовує або скомпільований Python-файл інтерфейсу, або завантажує .ui файл
        динамічно, залежно від налаштувань розробки. Це дозволяє швидко ітерувати
        дизайн без постійної перекомпіляції.
        """
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_ClassManagerDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/class_manager_dialog.ui", self)
            self.ui = cast(Ui_ClassManagerDialog, self)

    def _setup_state_variables(self) -> None:
        """
        Ініціалізує змінні стану та допоміжні віджети.

        Створює транслятор, віртуальну клавіатуру та ініціалізує кеш класів.
        """
        self.translator = QTranslator()
        self.lang_widget = KeyboardWidget(
            self.settings_service, self.keyboard_service, parent=self
        )
        self._waiting_classes = False
        self.cached_classes: List[ObjectClass] = []

    def _adjust_fields(self) -> None:
        """
        Налаштовує додаткові елементи інтерфейсу.

        Додає віджет клавіатури до відповідного макета та ініціює завантаження даних.
        """
        self.ui.keyboardLayout.addWidget(self.lang_widget)
        self._refresh_list()

    def _connect_handlers(self) -> None:
        """
        Підключає обробники сигналів до кнопок та списків.

        Налаштовує зв'язки для додавання, видалення, закриття вікна та
        обробки результатів мережевих запитів.
        """
        self.ui.btnAdd.clicked.connect(self._handle_save)
        self.ui.btnDelete.clicked.connect(self._delete_class)
        self.ui.btnClose.clicked.connect(self.accept)
        self.ui.lstClasses.itemClicked.connect(self._on_item_clicked)

        self.network_service.request_finished.connect(self._handle_db_status)

        if hasattr(self.ui, "btnClearSelection"):
            self.ui.btnClearSelection.clicked.connect(self._clear_selection)

    def _load_language(self) -> None:
        """
        Завантажує переклад інтерфейсу.

        !!! note
            Наразі реалізація мінімальна, оскільки основна логіка перекладу
            покладається на `retranslateUi`.
        """
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return
        QCoreApplication.removeTranslator(self.translator)

    def _populate_list(self, classes: Optional[List[ObjectClass]] = None):
        """
        Заповнює список класів у віджеті.

        Використовує `Qt.ItemDataRole.UserRole` для прихованого зберігання ID класу
        безпосередньо в елементі списку, що полегшує подальшу ідентифікацію при виборі.

        Args:
            classes: Список об'єктів класів для відображення. Якщо None, використовується кеш.
        """
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
        """
        Оновлює список класів, надсилаючи запит на сервер.
        """
        self._waiting_classes = True
        self.network_service.request_db_classes()
        print("[ClassManager] Loaded classes.")

    def _handle_db_status(self, response: ServiceResponse) -> None:
        """
        Обробляє відповіді від сервера щодо операцій з базою даних.

        Відповідає за оновлення локального кешу та інтерфейсу після успішних
        операцій або відображення помилок.

        Args:
            response: Об'єкт відповіді від мережевого сервісу.
        """

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

        print(f"[ObjectManager] DB Operation '{response.operation}': ...")

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """
        Обробляє вибір елемента у списку.

        Перемикає інтерфейс у режим редагування: заповнює поле вводу назвою
        вибраного класу та змінює текст кнопки на "Зберегти".

        Args:
            item: Елемент списку, на який натиснули.
        """
        self.ui.inpClassName.setText(item.text())
        self.ui.btnAdd.setText(self.tr("Save"))

    def _clear_selection(self) -> None:
        """
        Скидає вибір у списку та очищує поле вводу.

        Повертає інтерфейс у режим додавання нового класу.
        """
        self.ui.lstClasses.clearSelection()
        self.ui.inpClassName.clear()
        self.ui.btnAdd.setText(self.tr("Add"))

    def _handle_save(self) -> None:
        """
        Обробляє натискання кнопки збереження (Додати або Оновити).

        Визначає, чи потрібно створити новий клас, чи перейменувати існуючий,
        базуючись на наявності вибраного елемента у списку.
        """
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

            print(f"[ClassManager] Renaming class '{old_name}' to '{text}'...")
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
            print(f"[ClassManager] Adding new class '{text}'...")

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
        """
        Обробляє видалення вибраного класу.

        Запитує підтвердження у користувача перед відправкою запиту на сервер.
        """
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
            print(f"[ClassManager] Deleting class '{class_name}' (ID: {class_id})...")

            self.network_service.request_db_delete_class(class_id)

    def add_cache_class(self, class_obj: ObjectClass):
        """
        Додає новий клас до локального кешу та оновлює список.

        Args:
            class_obj: Об'єкт класу для додавання.
        """
        self.cached_classes.append(class_obj)
        self._populate_list()

    def update_cache_class(self, new_class_obj: ObjectClass):
        """
        Оновлює існуючий клас у локальному кеші.

        Args:
            new_class_obj: Об'єкт класу з оновленими даними.
        """
        # Використовуємо next() з генератором для швидкого пошуку індексу за ID
        index = next(
            (i for i, x in enumerate(self.cached_classes) if x.id == new_class_obj.id),
            None,
        )

        if index is not None:
            self.cached_classes[index] = new_class_obj
            self._populate_list()

    def delete_cache_class(self, id: int):
        """
        Видаляє клас із локального кешу за його ID.

        Args:
            id: Ідентифікатор класу для видалення.
        """
        index = next((i for i, x in enumerate(self.cached_classes) if x.id == id), None)

        if index is not None:
            self.cached_classes.pop(index)
            self._populate_list()

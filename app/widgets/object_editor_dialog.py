from typing import List, Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTranslator
from PyQt6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QMessageBox, QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED, RF_PARAMS__DIVIDER
from app.core.mixins import TestUIOptimizationMixin
from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.protocols import LangSettings
from app.services.keyboard_service import KeyboardService
from app.ui.ui_object_editor_dialog import Ui_ObjectEditorDialog
from app.utils.convert_measurement_unit import convert_hz_to_mhz, convert_mhz_to_hz
from app.widgets.keyboard_widget import KeyboardWidget


class ObjectEditorDialog(QDialog, TestUIOptimizationMixin):
    """
    Діалог додавання/редагування об'єкта.
    Логіка: RF та Sound є взаємовиключними (як RadioButton).
    """

    def __init__(
        self,
        settings_service: LangSettings,
        keyboard: KeyboardService,
        known_classes: List[ObjectClass],
        parent: Optional[QWidget] = None,
        object_data: Optional[DetectionObject] = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.object_classes: List[ObjectClass] = known_classes
        self.settings_service = settings_service
        self.keyboard_service = keyboard
        self.object_data: Optional[DetectionObject] = object_data
        self.is_edit_mode: bool = object_data is not None
        self.new_object: Optional[DetectionObject] = None

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()
        self._load_language()

        if not self.is_edit_mode:
            self.ui.chkRFEnable.setChecked(True)
            self._handle_toggle_rf_fields(True)
        else:
            self._toggle_rf_fields(self.ui.chkRFEnable.isChecked())
            self._toggle_sound_fields(self.ui.chkSoundEnable.isChecked())

        print(f"[ObjectEditor] Initialized. Edit mode: {self.is_edit_mode}")
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
            self.ui = Ui_ObjectEditorDialog()
            self.ui.setupUi(self)
        else:
            ui_path = "app/ui/object_editor_dialog.ui"
            uic.loadUi(ui_path, self)
            self.ui = cast(Ui_ObjectEditorDialog, self)

    def _setup_state_variables(self) -> None:
        self.translator = QTranslator()
        self.keyboard_widget = KeyboardWidget(
            self.settings_service, self.keyboard_service, parent=self
        )

    def _adjust_fields(self) -> None:
        self.ui.keyboardLayout.addWidget(self.keyboard_widget)

        self.update_classes_list(self.object_classes)

        if self.is_edit_mode and self.object_data:
            self.setWindowTitle(self.tr("Editing an object"))
            self._load_data_into_fields()
        else:
            self.setWindowTitle(self.tr("Adding a new object"))
            if self.ui.comboClass.count() > 0:
                self.ui.comboClass.setCurrentIndex(0)

    def _connect_handlers(self) -> None:
        self.ui.btnSave.clicked.connect(self._handle_save)
        self.ui.btnCancel.clicked.connect(self.reject)

        self.ui.chkRFEnable.toggled.connect(self._handle_toggle_rf_fields)
        self.ui.chkSoundEnable.toggled.connect(self._handle_toggle_sound_fields)

        self.ui.btnAddRF.clicked.connect(self._add_rf_range)
        self.ui.btnDelRF.clicked.connect(self._del_rf_range)
        self.ui.btnAddSound.clicked.connect(self._add_sound_freq)
        self.ui.btnDelSound.clicked.connect(self._del_sound_freq)

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return
        QCoreApplication.removeTranslator(self.translator)

    def update_classes_list(self, classes: List[ObjectClass]) -> None:
        self.object_classes = classes
        current_id = self.ui.comboClass.currentData()

        self.ui.comboClass.clear()

        for cls_obj in classes:
            self.ui.comboClass.addItem(cls_obj.name, userData=cls_obj.id)

        idx = self.ui.comboClass.findData(current_id)
        if idx >= 0:
            self.ui.comboClass.setCurrentIndex(idx)
        elif self.ui.comboClass.count() > 0:
            self.ui.comboClass.setCurrentIndex(0)

    def _load_data_into_fields(self) -> None:
        if not self.object_data:
            return

        obj = self.object_data

        # 1. Назва
        self.ui.inpName.setText(obj.name)

        # 2. Клас
        idx = -1
        if obj.class_id:
            idx = self.ui.comboClass.findData(obj.class_id)

        if idx == -1 and obj.object_class:
            idx = self.ui.comboClass.findText(obj.object_class)

        if idx >= 0:
            self.ui.comboClass.setCurrentIndex(idx)

        # 3. Небезпека
        self.ui.chkDangerous.setChecked(obj.is_dangerous)

        # 4. RF Params
        rf_list: List[str] = obj.rf_params_hz
        if rf_list:
            self.ui.chkRFEnable.setChecked(True)
            self.ui.lstRFFreqs.clear()
            for rf_str in rf_list:
                if isinstance(rf_str, str):
                    try:
                        parts = rf_str.split(RF_PARAMS__DIVIDER)
                        f_min = convert_hz_to_mhz(float(parts[0]))
                        f_max = convert_hz_to_mhz(float(parts[1]))
                        display_text = (
                            self.tr("{} MHz").format(f_min)
                            if f_min == f_max
                            else self.tr("{} - {} MHz").format(f_min, f_max)
                        )
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.ItemDataRole.UserRole, rf_str)
                        self.ui.lstRFFreqs.addItem(item)
                    except ValueError:
                        continue

        # 5. Sound Params
        snd_list: List[int] = obj.sound_params_hz
        if snd_list:
            self.ui.chkSoundEnable.setChecked(True)
            self.ui.lstSoundFreqs.clear()
            for freq in snd_list:
                item = QListWidgetItem(f"{freq} Гц")
                item.setData(Qt.ItemDataRole.UserRole, int(freq))
                self.ui.lstSoundFreqs.addItem(item)

        # Якщо в об'єкта були обидва списки (помилка даних), RF має пріоритет
        if rf_list:
            self.ui.chkSoundEnable.setChecked(False)
        elif snd_list:
            self.ui.chkRFEnable.setChecked(False)

    def _handle_save(self) -> None:
        name = self.ui.inpName.text().strip()
        if not name:
            print("[ObjectEditor] Save failed: Name is empty.")
            QMessageBox.warning(
                self, self.tr("Error"), self.tr("Enter the name of the object.")
            )
            return

        selected_class_id = self.ui.comboClass.currentData()
        selected_class_name = self.ui.comboClass.currentText()

        if selected_class_id is None:
            print("[ObjectEditor] Save failed: Class not selected.")
            QMessageBox.warning(self, self.tr("Error"), self.tr("Choose class."))
            return

        rf_data = self._collect_rf_data()
        sound_data = self._collect_sound_data()

        obj_id = self.object_data.id if self.is_edit_mode and self.object_data else None

        if rf_data is None and sound_data is None:
            print("[ObjectEditor] Save failed: No RF or Sound data.")
            return

        self.new_object = DetectionObject(
            id=obj_id,
            name=name,
            class_id=int(selected_class_id),
            object_class=selected_class_name,
            is_dangerous=self.ui.chkDangerous.isChecked(),
            rf_params_hz=rf_data or [],
            sound_params_hz=sound_data or [],
        )

        print(f"[ObjectEditor] Object saved: {name} (ClassID: {selected_class_id})")
        self.accept()

    def get_new_object(self) -> Optional[DetectionObject]:
        return self.new_object

    def _handle_toggle_rf_fields(self, enabled: bool) -> None:
        """Якщо вмикаємо RF, то вимикаємо Sound."""
        if enabled:
            self.ui.chkSoundEnable.blockSignals(True)
            self.ui.chkSoundEnable.setChecked(False)
            self.ui.chkSoundEnable.blockSignals(False)

            self._toggle_sound_fields(False)

        self._toggle_rf_fields(enabled)

    def _handle_toggle_sound_fields(self, enabled: bool) -> None:
        """Якщо вмикаємо Sound, то вимикаємо RF."""
        if enabled:
            self.ui.chkRFEnable.blockSignals(True)
            self.ui.chkRFEnable.setChecked(False)
            self.ui.chkRFEnable.blockSignals(False)

            self._toggle_rf_fields(False)

        self._toggle_sound_fields(enabled)

    def _toggle_rf_fields(self, enabled: bool) -> None:
        widgets = [
            self.ui.inpRFMin,
            self.ui.inpRFMax,
            self.ui.lstRFFreqs,
            self.ui.btnAddRF,
            self.ui.btnDelRF,
        ]
        for w in widgets:
            w.setEnabled(enabled)

        style = (
            ""
            if enabled
            else "background-color: rgba(50, 50, 50, 0.5); border: 1px solid #555;"
        )
        for w in [self.ui.inpRFMin, self.ui.inpRFMax, self.ui.lstRFFreqs]:
            w.setStyleSheet(style)

    def _toggle_sound_fields(self, enabled: bool) -> None:
        widgets = [
            self.ui.inpSoundFreq,
            self.ui.lstSoundFreqs,
            self.ui.btnAddSound,
            self.ui.btnDelSound,
        ]
        for w in widgets:
            w.setEnabled(enabled)

        style = (
            ""
            if enabled
            else "background-color: rgba(50, 50, 50, 0.5); border: 1px solid #555;"
        )
        for w in [self.ui.inpSoundFreq, self.ui.lstSoundFreqs]:
            w.setStyleSheet(style)

    def _check_is_duplicate(
        self,
        list_widget: QListWidget,
        value_to_check: str | int,
        check_range: tuple[int, int] | None = None,
    ) -> bool:
        """
        Перевіряє на дублікати та опційно на перетин діапазонів.
        """
        role = Qt.ItemDataRole.UserRole

        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item is None:
                continue

            existing_data = item.data(role)

            # Перевірка на повний дублікат
            if existing_data == value_to_check:
                QMessageBox.warning(
                    self,
                    self.tr("Error"),
                    self.tr("This value has already been added to the list!"),
                )
                return True

            # Перевірка на перетин діапазонів
            if check_range is not None and isinstance(existing_data, str):
                try:
                    ex_min_str, ex_max_str = existing_data.split("-")
                    ex_min, ex_max = int(ex_min_str), int(ex_max_str)

                    new_min, new_max = check_range

                    if new_min <= ex_max and ex_min <= new_max:
                        QMessageBox.warning(
                            self,
                            self.tr("Error"),
                            self.tr("Range overlaps with existing: {}-{} MHz").format(
                                convert_hz_to_mhz(ex_min), convert_hz_to_mhz(ex_max)
                            ),
                        )
                        return True
                except ValueError:
                    continue

        return False

    def _add_rf_range(self) -> None:
        f_min = self.ui.inpRFMin.value()
        f_max = self.ui.inpRFMax.value()

        if f_min <= 0 or f_max <= 0:
            return
        if f_min > f_max:
            f_min, f_max = f_max, f_min
            self.ui.inpRFMin.setValue(f_min)
            self.ui.inpRFMax.setValue(f_max)

        f_min_hz = convert_mhz_to_hz(f_min)
        f_max_hz = convert_mhz_to_hz(f_max)
        raw_string = f"{f_min_hz}-{f_max_hz}"

        if self._check_is_duplicate(
            self.ui.lstRFFreqs, raw_string, (f_min_hz, f_max_hz)
        ):
            return

        display_text = (
            self.tr("{} MHz").format(f_min)
            if f_min == f_max
            else self.tr("{} - {} MHz").format(f_min, f_max)
        )

        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, raw_string)
        self.ui.lstRFFreqs.addItem(item)

    def _del_rf_range(self) -> None:
        row = self.ui.lstRFFreqs.currentRow()
        if row >= 0:
            self.ui.lstRFFreqs.takeItem(row)

    def _add_sound_freq(self) -> None:
        freq = self.ui.inpSoundFreq.value()
        if freq <= 0:
            return

        text = self.tr("{} Hz").format(freq)

        if self._check_is_duplicate(self.ui.lstSoundFreqs, int(freq)):
            return

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, int(freq))
        self.ui.lstSoundFreqs.addItem(item)

    def _del_sound_freq(self) -> None:
        row = self.ui.lstSoundFreqs.currentRow()
        if row >= 0:
            self.ui.lstSoundFreqs.takeItem(row)

    def _collect_rf_data(self) -> Optional[List[str]]:
        data: List[str] = []
        if self.ui.chkRFEnable.isChecked():
            for i in range(self.ui.lstRFFreqs.count()):
                item = self.ui.lstRFFreqs.item(i)
                if item is None:
                    continue

                val = item.data(Qt.ItemDataRole.UserRole)
                if val is not None:
                    data.append(str(val))

        if len(data) == 0:
            return None

        return data

    def _collect_sound_data(self) -> Optional[List[int]]:
        data: List[int] = []
        if self.ui.chkSoundEnable.isChecked():
            for i in range(self.ui.lstSoundFreqs.count()):
                item = self.ui.lstSoundFreqs.item(i)
                if item is None:
                    continue

                val = item.data(Qt.ItemDataRole.UserRole)
                if val is not None:
                    data.append(int(val))

        if len(data) == 0:
            return None

        return data

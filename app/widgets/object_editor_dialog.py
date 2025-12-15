from PyQt6.QtWidgets import QDialog, QMessageBox, QListWidgetItem
from PyQt6.QtCore import Qt, QEvent, QCoreApplication
from PyQt6 import uic

from app.protocols import ObjectEditorDialogSettings
from app.ui.ui_object_editor_dialog import Ui_ObjectEditorDialog
from app.models.detection_object import DetectionObject


class ObjectEditorDialog(QDialog):
    """
    Логіка редагування.
    RF: Підтримка декількох діапазонів (Від-До).
    Sound: Підтримка списку частот.
    """

    def __init__(
        self,
        settings_service: ObjectEditorDialogSettings,
        parent=None,
        object_data=None,
    ):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.settings_service = settings_service
        self.object_data = object_data
        self.is_edit_mode = object_data is not None

        self._load_ui()
        self._adjust_fields()
        self._connect_handlers()

        self._load_language()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_ObjectEditorDialog()
            self.ui.setupUi(self)
        else:
            ui_path = "app/ui/object_editor_dialog.ui"

            uic.loadUi(ui_path, self)
            self.ui = self

    def _adjust_fields(self):
        if self.is_edit_mode:
            self.setWindowTitle("Редагування об'єкта")
            self._load_data_into_fields()
        else:
            self.setWindowTitle("Додавання нового об'єкта")

        self._toggle_rf_fields(self.ui.chkRFEnable.isChecked())
        self._toggle_sound_fields(self.ui.chkSoundEnable.isChecked())

    def _connect_handlers(self):
        self.ui.btnSave.clicked.connect(self._handle_save)
        self.ui.btnCancel.clicked.connect(self.reject)

        self.ui.chkRFEnable.toggled.connect(self._toggle_rf_fields)
        self.ui.chkSoundEnable.toggled.connect(self._toggle_sound_fields)

        self.ui.btnAddRF.clicked.connect(self._add_rf_range)
        self.ui.btnDelRF.clicked.connect(self._del_rf_range)
        self.ui.btnAddSound.clicked.connect(self._add_sound_freq)
        self.ui.btnDelSound.clicked.connect(self._del_sound_freq)

    def _load_language(self):
        lang_code = self.settings_service.lang_code

        # if lang_code == None:
        #     return

        # QCoreApplication.removeTranslator(self.translator)

    def _toggle_rf_fields(self, enabled):
        # Активуємо/деактивуємо поля RF
        for w in [
            self.ui.inpRFMin,
            self.ui.inpRFMax,
            self.ui.lstRFFreqs,
            self.ui.btnAddRF,
            self.ui.btnDelRF,
        ]:
            w.setEnabled(enabled)

        style = (
            ""
            if enabled
            else "background-color: rgba(50, 50, 50, 0.5); border: 1px solid #555;"
        )
        for w in [self.ui.inpRFMin, self.ui.inpRFMax, self.ui.lstRFFreqs]:
            w.setStyleSheet(style)

    def _toggle_sound_fields(self, enabled):
        for w in [
            self.ui.inpSoundFreq,
            self.ui.lstSoundFreqs,
            self.ui.btnAddSound,
            self.ui.btnDelSound,
        ]:
            w.setEnabled(enabled)

        style = (
            ""
            if enabled
            else "background-color: rgba(50, 50, 50, 0.5); border: 2px solid #555;"
        )
        for w in [self.ui.inpSoundFreq, self.ui.lstSoundFreqs]:
            w.setStyleSheet(style)

    def _add_rf_range(self):
        f_min = self.ui.inpRFMin.value()
        f_max = self.ui.inpRFMax.value()

        if f_min <= 0 or f_max <= 0:
            return

        if f_min > f_max:
            f_min, f_max = f_max, f_min
            self.ui.inpRFMin.setValue(f_min)
            self.ui.inpRFMax.setValue(f_max)

        if f_min == f_max:
            text = f"{f_min} МГц"
        else:
            text = f"{f_min} - {f_max} МГц"

        item = QListWidgetItem(text)

        item.setData(Qt.ItemDataRole.UserRole, {"min_mhz": f_min, "max_mhz": f_max})
        self.ui.lstRFFreqs.addItem(item)

    def _del_rf_range(self):
        row = self.ui.lstRFFreqs.currentRow()
        if row >= 0:
            self.ui.lstRFFreqs.takeItem(row)

    def _add_sound_freq(self):
        freq = self.ui.inpSoundFreq.value()
        if freq <= 0:
            return

        text = f"{freq} Гц"

        existing = [
            self.ui.lstSoundFreqs.item(i).text()
            for i in range(self.ui.lstSoundFreqs.count())
        ]
        if text in existing:
            return

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, freq)
        self.ui.lstSoundFreqs.addItem(item)

    def _del_sound_freq(self):
        row = self.ui.lstSoundFreqs.currentRow()
        if row >= 0:
            self.ui.lstSoundFreqs.takeItem(row)

    def _load_data_into_fields(self):
        d = self.object_data
        self.ui.inpName.setText(d.get("name", ""))
        self.ui.inpClass.setText(d.get("object_class", "unknown"))
        self.ui.chkDangerous.setChecked(d.get("is_dangerous", False))

        rf_list = d.get("rf_params", [])
        if rf_list:
            self.ui.chkRFEnable.setChecked(True)
            for rf in rf_list:

                if "min_mhz" in rf:
                    f_min = rf["min_mhz"]
                    f_max = rf["max_mhz"]
                else:

                    center = rf.get("freq_mhz", 0)
                    bw = rf.get("bandwidth", 0)
                    f_min = center - (bw / 2) if bw > 0 else center
                    f_max = center + (bw / 2) if bw > 0 else center

                text = f"{f_min} МГц" if f_min == f_max else f"{f_min} - {f_max} МГц"
                item = QListWidgetItem(text)
                item.setData(
                    Qt.ItemDataRole.UserRole, {"min_mhz": f_min, "max_mhz": f_max}
                )
                self.ui.lstRFFreqs.addItem(item)
        else:
            self.ui.chkRFEnable.setChecked(False)

        snd_list = d.get("sound_params", [])
        if snd_list:
            self.ui.chkSoundEnable.setChecked(True)
            for freq in snd_list:
                item = QListWidgetItem(f"{freq} Гц")
                item.setData(Qt.ItemDataRole.UserRole, freq)
                self.ui.lstSoundFreqs.addItem(item)
        else:
            self.ui.chkSoundEnable.setChecked(False)

    def _handle_save(self):
        name = self.ui.inpName.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Введіть назву об'єкта.")
            return

        rf_data = []
        if self.ui.chkRFEnable.isChecked():
            for i in range(self.ui.lstRFFreqs.count()):
                item = self.ui.lstRFFreqs.item(i)
                rf_data.append(item.data(Qt.ItemDataRole.UserRole))

        sound_data = []
        if self.ui.chkSoundEnable.isChecked():
            for i in range(self.ui.lstSoundFreqs.count()):
                item = self.ui.lstSoundFreqs.item(i)
                sound_data.append(item.data(Qt.ItemDataRole.UserRole))

        target_obj = DetectionObject(
            id=self.object_data["id"] if self.is_edit_mode else None,
            name=name,
            object_class=self.ui.inpClass.text().strip(),
            is_dangerous=self.ui.chkDangerous.isChecked(),
            rf_params=rf_data,
            sound_params=sound_data,
        )

        self.new_object = target_obj

        self.accept()

    def get_new_object(self) -> DetectionObject:
        return self.new_object

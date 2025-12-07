"""
Діалог редагування об'єктів.
Логіка вікна: додавання, редагування та видалення об'єктів детекції.
"""

import os
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import Qt, QEvent
from PyQt6 import uic

# Імпорт UI (якщо згенерований)
from app.ui.ui_object_editor_dialog import Ui_ObjectEditorDialog

# Імпорт Моделі
from app.models.detection_object import DetectionObject


class ObjectEditorDialog(QDialog):
    """
    Логіка діалогового вікна редагування об'єктів.
    """

    def __init__(self, db_service, settings_service, parent=None, object_data=None):
        super().__init__(parent)
        print("[ObjectEditorDialog] Ініціалізація діалогу редагування...")

        self.db_service = db_service
        self.settings_service = settings_service
        self.object_data = object_data  # Це словник (dict) з БД
        self.is_edit_mode = object_data is not None

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()

        print("[ObjectEditorDialog] Діалог готовий.")

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
            ui_path = os.path.join(
                os.path.dirname(__file__), "../ui/object_editor_dialog.ui"
            )
            uic.loadUi(ui_path, self)
            self.ui = self

    def _setup_state_variables(self):
        pass

    def _adjust_fields(self):
        """Налаштування полів."""
        if self.is_edit_mode:
            self.setWindowTitle("Редагування об'єкта")
            self._load_data_into_fields()
        else:
            self.setWindowTitle("Додавання нового об'єкта")
            self.ui.btnDelete.setVisible(False)

        # Синхронізація стану полів
        self._toggle_rf_fields(self.ui.chkRFEnable.isChecked())
        self._toggle_audio_fields(self.ui.chkAudioEnable.isChecked())

    def _connect_handlers(self):
        self.ui.btnSave.clicked.connect(self._handle_save)
        self.ui.btnCancel.clicked.connect(self.reject)
        self.ui.btnDelete.clicked.connect(self._handle_delete)

        self.ui.chkRFEnable.toggled.connect(self._toggle_rf_fields)
        self.ui.chkAudioEnable.toggled.connect(self._toggle_audio_fields)

    def _toggle_rf_fields(self, enabled):
        self.ui.inpRFFreq.setEnabled(enabled)
        self.ui.inpRFBw.setEnabled(enabled)
        self._apply_disabled_style([self.ui.inpRFFreq, self.ui.inpRFBw], enabled)

    def _toggle_audio_fields(self, enabled):
        self.ui.inpAudioMin.setEnabled(enabled)
        self.ui.inpAudioMax.setEnabled(enabled)
        self._apply_disabled_style([self.ui.inpAudioMin, self.ui.inpAudioMax], enabled)

    def _apply_disabled_style(self, widgets, enabled):
        style = ""
        if not enabled:
            style = "background-color: rgba(50, 50, 50, 0.5); border: 2px solid #555;"

        for w in widgets:
            w.setStyleSheet(style)

    def _load_data_into_fields(self):
        """
        Заповнює форму даними.
        Тут ми працюємо з dict, бо він прийшов з JSON.
        """
        d = self.object_data

        self.ui.inpName.setText(d.get("name", ""))

        idx = self.ui.inpClass.findText(d.get("object_class", "unknown"))
        if idx >= 0:
            self.ui.inpClass.setCurrentIndex(idx)

        self.ui.chkDangerous.setChecked(d.get("is_dangerous", False))

        rf = d.get("rf_params")
        if rf:
            self.ui.chkRFEnable.setChecked(True)
            self.ui.inpRFFreq.setValue(rf.get("freq_mhz", 2400.0))
            self.ui.inpRFBw.setValue(rf.get("bandwidth", 20.0))
        else:
            self.ui.chkRFEnable.setChecked(False)

        aud = d.get("audio_params")
        if aud:
            self.ui.chkAudioEnable.setChecked(True)
            self.ui.inpAudioMin.setValue(aud.get("min_freq", 100))
            self.ui.inpAudioMax.setValue(aud.get("max_freq", 5000))
        else:
            self.ui.chkAudioEnable.setChecked(False)

    def _handle_save(self):
        """Збір даних через модель DetectionObject."""
        print("[ObjectEditorDialog] Збереження даних...")
        name = self.ui.inpName.text().strip()

        if not name:
            QMessageBox.warning(self, "Помилка", "Будь ласка, введіть назву об'єкта.")
            self.ui.inpName.setFocus()
            return

        # 1. Підготовка під-структур
        rf_data = None
        if self.ui.chkRFEnable.isChecked():
            rf_data = {
                "freq_mhz": self.ui.inpRFFreq.value(),
                "bandwidth": self.ui.inpRFBw.value(),
            }

        audio_data = None
        if self.ui.chkAudioEnable.isChecked():
            audio_data = {
                "min_freq": self.ui.inpAudioMin.value(),
                "max_freq": self.ui.inpAudioMax.value(),
            }

        # 2. Визначення ID (None для створення, існуючий для редагування)
        target_id = self.object_data["id"] if self.is_edit_mode else None

        # 3. Створення об'єкта моделі
        try:
            target_obj = DetectionObject(
                id=target_id,
                name=name,
                object_class=self.ui.inpClass.currentText(),
                is_dangerous=self.ui.chkDangerous.isChecked(),
                rf_params=rf_data,
                audio_params=audio_data,
            )
        except Exception as e:
            QMessageBox.critical(self, "Помилка даних", f"Некоректні дані: {e}")
            return

        # 4. Відправка (серіалізація в dict)
        if self.is_edit_mode:
            print(f"[ObjectEditor] Оновлення: {target_obj.name} (ID: {target_obj.id})")
            self.db_service.update_object(target_obj.to_dict())
        else:
            print(f"[ObjectEditor] Створення нового: {target_obj.name}")
            self.db_service.add_object(target_obj.to_dict())

        self.accept()

    def _handle_delete(self):
        confirm = QMessageBox.question(
            self,
            "Підтвердження видалення",
            f"Ви впевнені, що хочете видалити об'єкт '{self.ui.inpName.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            if self.is_edit_mode and "id" in self.object_data:
                print(f"[ObjectEditor] Видалення ID: {self.object_data['id']}")
                self.db_service.delete_object(self.object_data["id"])
            self.accept()

    def _handle_logout(self):
        confirm = QMessageBox.question(
            self,
            "Вихід",
            "Вийти з акаунту та перезапустити програму?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            print("[ObjectEditorDialog] Вихід з акаунту...")
            if self.parent() and hasattr(self.parent(), "restart_app"):
                self.parent().restart_app()
            self.close()

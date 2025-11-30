from PyQt6.QtWidgets import QWidget
from PyQt6 import uic
from PyQt6.QtCore import QEvent, QCoreApplication, QTranslator
import os

from app.ui.ui_keyboard_widget import Ui_KeyboardWidget
from app.services.keyboard_service import KeyboardService
from app.protocols import KeyboardWidgetSettings


class KeyboardWidget(QWidget):
    def __init__(
        self,
        settings: KeyboardWidgetSettings,
        keyboard_service: KeyboardService,
        parent=None,
    ):
        super().__init__(parent)

        self.settings_service = settings
        self.keyboard_service = keyboard_service

        self._load_ui()

        self._setup_state_variables()

        self._adjust_fields()

        self._connect_handlers()

        self._load_language()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("Зміна мови, оновлюю UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_KeyboardWidget()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/keyboard_widget.ui", self)
            self.ui = self

    def _setup_state_variables(self):
        self.translator = QTranslator()
        self.keyboard_service.set_callback(self.update_ui_silent)

    def _adjust_fields(self):
        self.update_ui_silent(self.keyboard_service.current_layout)

    def _connect_handlers(self):
        self.ui.langComboBox.currentTextChanged.connect(self._on_ui_change)

    def _load_language(self):
        lang_code = self.settings_service.lang_code

        if lang_code == None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    def update_ui_silent(self, layout_code):

        self.ui.langComboBox.blockSignals(True)

        index = self.ui.langComboBox.findText(layout_code)
        if index != -1:
            self.ui.langComboBox.setCurrentIndex(index)

        self.ui.langComboBox.blockSignals(False)

    def _on_ui_change(self, text):

        print(f"UI Request to change layout to: {text}")

        if self.keyboard_service.current_layout != text:
            self.keyboard_service.toggle_layout()

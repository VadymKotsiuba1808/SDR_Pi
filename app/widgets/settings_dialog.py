from dataclasses import dataclass
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import Qt, QEvent, QTranslator, QCoreApplication, QTimer
from PyQt6 import uic

from app.protocols import SettingsDialogSettings
from app.ui.ui_settings_dialog import Ui_SettingsDialog
from app.utils.system_utils import restart_process


@dataclass
class SettingsData:
    """Клас для зберігання налаштувань діалогу"""

    radar_max_radius: float = 1000.0
    gps_interval_s: int = 300
    main_relay: str = "K1"


class SettingsDialog(QDialog):
    """
    Сторінка налаштувань.
    Логіка відображення та зміни конфігурації системи (радіус дії, гучність, системні параметри).
    """

    def __init__(self, settings_service: SettingsDialogSettings = None, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.settings_service = settings_service
        self.translator = QTranslator()

        self._load_ui()
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
            self.ui = Ui_SettingsDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/settings_dialog.ui", self)
            self.ui = self

    def _adjust_fields(self):
        s = self.settings_service

        self.ui.inpMaxRadius.setValue(s.radar_max_radius / 1000)
        self.ui.inpGpsInterval.setValue(s.gps_interval_s / 60)

        relay_val = s.main_relay
        index = self.ui.cmbRelay.findText(relay_val)
        if index >= 0:
            self.ui.cmbRelay.setCurrentIndex(index)

    def _connect_handlers(self):
        self.ui.btnSave.clicked.connect(self._handle_save)
        self.ui.btnCancel.clicked.connect(self.reject)
        self.ui.btnLogout.clicked.connect(self.restart_app)

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

    def restart_app(self):
        self.settings_service.remember_me = False
        self.setEnabled(False)
        print("Performing restart...")

        restart_process()

    def _handle_save(self):
        self.new_settings = SettingsData(
            radar_max_radius=int(self.ui.inpMaxRadius.value() * 1000),
            gps_interval_s=int(self.ui.inpGpsInterval.value() * 60),
            main_relay=self.ui.cmbRelay.currentText(),
        )

        print(f"[SettingsDialog] Збережено: {self.new_settings}")
        self.accept()

    def get_settings(self) -> SettingsData:
        return getattr(self, "new_settings", {})

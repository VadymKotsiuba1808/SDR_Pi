from dataclasses import dataclass, field
from typing import Optional, List

from PyQt6.QtWidgets import QDialog, QWidget
from PyQt6.QtCore import Qt, QEvent, QTranslator, QCoreApplication
from PyQt6 import uic

from app.protocols import SettingsDialogSettings
from app.ui.ui_settings_dialog import Ui_SettingsDialog
from app.utils.system_utils import restart_process


@dataclass
class SettingsData:
    """Клас для зберігання налаштувань діалогу (DTO)."""

    radar_max_radius: float = 1000.0
    gps_interval_s: int = 120
    main_relay: List[str] = field(default_factory=lambda: ["K1"])


class SettingsDialog(QDialog):
    """
    Сторінка налаштувань.
    Логіка відображення та зміни конфігурації системи.
    """

    def __init__(
        self,
        settings_service: SettingsDialogSettings,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.settings_service = settings_service
        self.translator = QTranslator()

        self.new_settings: Optional[SettingsData] = None

        self._load_ui()
        self._adjust_fields()
        self._connect_handlers()
        self._load_language()

        print("[Settings] Dialog initialized.")

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("[Settings] Language change detected, retranslating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_SettingsDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/settings_dialog.ui", self)
            self.ui = self

    def _adjust_fields(self) -> None:
        s = self.settings_service

        self.ui.inpMaxRadius.setValue(s.radar_max_radius / 1000)
        self.ui.inpGpsInterval.setValue(s.gps_interval_s)

        relay_val = ",".join(s.main_relay)
        index = self.ui.cmbRelay.findText(relay_val)
        if index >= 0:
            self.ui.cmbRelay.setCurrentIndex(index)

    def _connect_handlers(self) -> None:
        self.ui.btnSave.clicked.connect(self._handle_save)
        self.ui.btnCancel.clicked.connect(self.reject)
        self.ui.btnLogout.clicked.connect(self.restart_app)

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code

        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
            print(f"[Settings] Loaded translation: {path}")
        else:
            print(f"[Settings] Error: Failed to load translation file: {path}")

    def restart_app(self) -> None:
        print("[Settings] Initiating application restart...")
        self.settings_service.remember_me = False
        self.setEnabled(False)

        restart_process()

    def _handle_save(self) -> None:
        radius_m = float(self.ui.inpMaxRadius.value() * 1000)
        gps_interval = int(self.ui.inpGpsInterval.value())
        relays = self.ui.cmbRelay.currentText().split(",")

        self.new_settings = SettingsData(
            radar_max_radius=radius_m,
            gps_interval_s=gps_interval,
            main_relay=relays,
        )

        print(f"[Settings] Configuration saved: {self.new_settings}")
        self.accept()

    def get_settings(self) -> Optional[SettingsData]:
        return self.new_settings

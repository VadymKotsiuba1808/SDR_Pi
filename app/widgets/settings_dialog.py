from dataclasses import dataclass, field
from typing import Optional, List
from itertools import combinations

from PyQt6.QtWidgets import QDialog, QWidget
from PyQt6.QtCore import Qt, QEvent, QTranslator, QCoreApplication
from PyQt6 import uic

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.protocols import SettingsDialogSettings
from app.ui.ui_settings_dialog import Ui_SettingsDialog
from app.utils.system_utils import restart_process
from app.utils.ui_utils import update_element_styles

from app.core.constants import RELAY_NAMES_LIST


@dataclass
class SettingsData:
    """Клас для зберігання налаштувань діалогу (DTO)."""

    radar_max_radius_km: float = 200.0
    gps_interval_s: int = 120
    main_relays: List[str] = field(default_factory=lambda: [RELAY_NAMES_LIST[0]])
    is_jammer_auto_start_enabled: bool = False
    is_jammer_auto_stop_enabled: bool = False
    jammer_auto_stop_interval_s: int = 900


RELAYS_DIVIDER = ", "


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
            if DEV_COMPILED_UI_USING_ENABLED:
                print("[Settings] Language change detected, retranslating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_SettingsDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/settings_dialog.ui", self)
            self.ui = self

    def _adjust_fields(self) -> None:
        s = self.settings_service

        self.ui.inpMaxRadius.setValue(s.radar_max_radius_km)
        self.ui.inpGpsInterval.setValue(s.gps_interval_s)

        self._populate_relay_cmb()

        relay_val = RELAYS_DIVIDER.join(s.main_relays)
        index = self.ui.cmbRelay.findText(relay_val)
        if index >= 0:
            self.ui.cmbRelay.setCurrentIndex(index)

        self.ui.chkJammerAutoStart.setChecked(s.is_jammer_auto_start_enabled)
        self.ui.chkJammerAutoStop.setChecked(s.is_jammer_auto_stop_enabled)

        self.ui.inpJammerStopInterval.setValue(s.jammer_auto_stop_interval_s)

    def _populate_relay_cmb(self):
        self.ui.cmbRelay.clear()
        self.ui.cmbRelay.blockSignals(True)

        n = len(RELAY_NAMES_LIST)
        for r in range(1, n + 1):
            for combo in combinations(RELAY_NAMES_LIST, r):
                self.ui.cmbRelay.addItem(RELAYS_DIVIDER.join(combo))

        self.ui.cmbRelay.blockSignals(False)

    def _connect_handlers(self) -> None:
        self.ui.chkJammerAutoStop.toggled.connect(self.handle_auto_stop_enabled)

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

    def handle_auto_stop_enabled(self, isChecked: bool) -> None:
        self.ui.inpJammerStopInterval.setEnabled(isChecked)
        update_element_styles(self.ui.inpJammerStopInterval)

    def restart_app(self) -> None:
        print("[Settings] Initiating application restart...")
        self.settings_service.remember_me = False
        self.setEnabled(False)

        restart_process()

    def _handle_save(self) -> None:
        radius_km = self.ui.inpMaxRadius.value()
        gps_interval = int(self.ui.inpGpsInterval.value())
        relays = self.ui.cmbRelay.currentText().split(RELAYS_DIVIDER)
        auto_start_enabled = self.ui.chkJammerAutoStart.isChecked()
        auto_stop_enabled = self.ui.chkJammerAutoStop.isChecked()

        auto_stop_interval_s = self.ui.inpJammerStopInterval.value()

        self.new_settings = SettingsData(
            radar_max_radius_km=radius_km,
            gps_interval_s=gps_interval,
            main_relays=relays,
            is_jammer_auto_start_enabled=auto_start_enabled,
            is_jammer_auto_stop_enabled=auto_stop_enabled,
            jammer_auto_stop_interval_s=auto_stop_interval_s,
        )

        print(f"[Settings] Configuration saved: {self.new_settings}")
        self.accept()

    def get_settings(self) -> Optional[SettingsData]:
        return self.new_settings

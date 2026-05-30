from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTranslator
from PyQt6.QtWidgets import QDialog, QWidget

from app.core.constants import (
    CLEAN_TARGET_NAME,
    DEV_COMPILED_UI_USING_ENABLED,
    RELAY_NAMES_LIST,
)
from app.models.settings import CleanRule
from app.protocols import SettingsDialogSettings
from app.ui.ui_settings_dialog import Ui_SettingsDialog
from app.utils.system_utils import restart_process
from app.utils.ui_utils import update_element_styles


@dataclass
class SettingsData:
    """Клас для зберігання налаштувань діалогу (DTO)."""

    radar_max_radius_km: float = 200.0
    gps_interval_s: int = 120
    main_relays: List[str] = field(default_factory=lambda: [RELAY_NAMES_LIST[0]])
    detection_ttl_s: int = 3
    is_jammer_auto_start_enabled: bool = False
    is_jammer_auto_stop_enabled: bool = False
    jammer_auto_stop_interval_s: int = 900

    clean_settings: Dict[str, CleanRule] = field(default_factory=dict)


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

        self._load_ui()
        self._setup_state_variables()
        self._setup_clean_ui_logic()
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

    def _setup_state_variables(self):
        self.translator = QTranslator()

        self.new_settings: Optional[SettingsData] = None

        self.clean_settings_buffer: Dict[CLEAN_TARGET_NAME, CleanRule] = (
            self.settings_service.clean_settings.copy()
        )
        self.current_clean_target_key: Optional[CLEAN_TARGET_NAME] = None

    def _adjust_fields(self) -> None:
        s = self.settings_service

        self.ui.inpMaxRadius.setValue(s.radar_max_radius_km)
        self.ui.inpGpsInterval.setValue(s.gps_interval_s)
        self.ui.inpDetectionTTL.setValue(s.detection_ttl_s)

        self._populate_relay_cmb()

        relay_val = RELAYS_DIVIDER.join(s.main_relays)
        index = self.ui.cmbRelay.findText(relay_val)
        if index >= 0:
            self.ui.cmbRelay.setCurrentIndex(index)

        self.ui.chkJammerAutoStart.setChecked(s.is_jammer_auto_start_enabled)
        self.ui.chkJammerAutoStop.setChecked(s.is_jammer_auto_stop_enabled)

        self.ui.inpJammerStopInterval.setValue(s.jammer_auto_stop_interval_s)
        self.handle_auto_stop_enabled(s.is_jammer_auto_stop_enabled)

        if self.ui.cmbCleanTarget.count() > 0:
            self.ui.cmbCleanTarget.setCurrentIndex(0)
            self._load_clean_settings_to_ui(0)

    def _populate_relay_cmb(self):
        self.ui.cmbRelay.clear()
        self.ui.cmbRelay.blockSignals(True)

        n = len(RELAY_NAMES_LIST)
        for r in range(1, n + 1):
            for combo in combinations(RELAY_NAMES_LIST, r):
                self.ui.cmbRelay.addItem(RELAYS_DIVIDER.join(combo))

        self.ui.cmbRelay.blockSignals(False)

    def _setup_clean_ui_logic(self):
        """Заповнює ComboBox і налаштовує сигнали для блоку очистки."""
        self.ui.cmbCleanTarget.clear()

        TARGET_DISPLAY_NAMES = {
            CLEAN_TARGET_NAME.LOGS: self.tr("Logs"),
            CLEAN_TARGET_NAME.SCREENSHOTS: self.tr("Screenshots"),
            CLEAN_TARGET_NAME.SCREEN_RECORDS: self.tr("Screen records"),
        }

        for target in CLEAN_TARGET_NAME:
            display_name = TARGET_DISPLAY_NAMES.get(target, target.value)

            self.ui.cmbCleanTarget.addItem(display_name, userData=target)

    def _connect_handlers(self) -> None:
        self.ui.chkJammerAutoStop.toggled.connect(self.handle_auto_stop_enabled)

        self.ui.cmbCleanTarget.currentIndexChanged.connect(
            self._on_clean_target_changed
        )
        self.ui.chkCleanEnabled.toggled.connect(self._handle_clean_enabled_toggled)

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

    def _on_clean_target_changed(self, index: int):
        """Зберігає поточні дані в буфер і завантажує нові при зміні папки."""
        if index < 0:
            return

        self._save_current_clean_target_to_buffer()

        self._load_clean_settings_to_ui(index)

    def _save_current_clean_target_to_buffer(self):
        """Зчитує UI і оновлює буфер для поточної активної вкладки."""
        if self.current_clean_target_key:
            rule = CleanRule(
                enabled=self.ui.chkCleanEnabled.isChecked(),
                days=self.ui.inpCleanDays.value(),
            )
            self.clean_settings_buffer[self.current_clean_target_key] = rule

    def _load_clean_settings_to_ui(self, index: int):
        """Завантажує дані з буфера в UI для обраного індексу."""
        target_key = self.ui.cmbCleanTarget.itemData(index)
        self.current_clean_target_key = target_key

        rule = None
        if target_key in self.clean_settings_buffer:
            rule = self.clean_settings_buffer[target_key]

        self.ui.chkCleanEnabled.blockSignals(True)
        self.ui.inpCleanDays.blockSignals(True)

        if rule:
            self.ui.chkCleanEnabled.setChecked(rule.enabled)
            self.ui.inpCleanDays.setValue(rule.days)
        else:
            self.ui.chkCleanEnabled.setChecked(False)
            self.ui.inpCleanDays.setValue(30)

        self.ui.inpCleanDays.setEnabled(self.ui.chkCleanEnabled.isChecked())
        update_element_styles(self.ui.inpCleanDays)

        self.ui.chkCleanEnabled.blockSignals(False)
        self.ui.inpCleanDays.blockSignals(False)

    def _handle_clean_enabled_toggled(self, is_checked: bool):
        """Обробка візуального стану поля днів."""
        self.ui.inpCleanDays.setEnabled(is_checked)
        update_element_styles(self.ui.inpCleanDays)

    def handle_auto_stop_enabled(self, isChecked: bool) -> None:
        self.ui.inpJammerStopInterval.setEnabled(isChecked)
        update_element_styles(self.ui.inpJammerStopInterval)

    def restart_app(self) -> None:
        print("[Settings] Initiating application restart...")
        self.settings_service.remember_me = False
        self.setEnabled(False)

        restart_process()

    def _handle_save(self) -> None:
        self._save_current_clean_target_to_buffer()

        radius_km = self.ui.inpMaxRadius.value()
        gps_interval = int(self.ui.inpGpsInterval.value())
        detection_ttl = int(self.ui.inpDetectionTTL.value())
        relays = self.ui.cmbRelay.currentText().split(RELAYS_DIVIDER)
        auto_start_enabled = self.ui.chkJammerAutoStart.isChecked()
        auto_stop_enabled = self.ui.chkJammerAutoStop.isChecked()

        auto_stop_interval_s = self.ui.inpJammerStopInterval.value()

        self.new_settings = SettingsData(
            radar_max_radius_km=radius_km,
            gps_interval_s=gps_interval,
            detection_ttl_s=detection_ttl,
            main_relays=relays,
            is_jammer_auto_start_enabled=auto_start_enabled,
            is_jammer_auto_stop_enabled=auto_stop_enabled,
            jammer_auto_stop_interval_s=auto_stop_interval_s,
            clean_settings=self.clean_settings_buffer,
        )

        print(f"[Settings] Configuration saved: {self.new_settings}")
        self.accept()

    def get_settings(self) -> Optional[SettingsData]:
        return self.new_settings

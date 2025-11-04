from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSlot, QSize
from PyQt6.QtGui import QIcon
from PyQt6 import uic
import os

from app.ui.ui_record_status_widget import Ui_RecordingStatusWidget
from app.services.settings_service import SettingsService
from app.utils.ui_utils import update_element_styles


class RecordingStatusWidget(QWidget):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)

        self.settings_service = settings

        self._load_ui()

        self.setVisible(False)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_RecordingStatusWidget()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/record_status_widget.ui", self)
            self.ui = self

    @pyqtSlot(str)
    def update_duration(self, time_str):
        self.ui.duration_label.setText(time_str)

    @pyqtSlot(bool)
    def on_pause_toggled(self, is_paused):

        if is_paused:
            self.ui.rec_label.setProperty("active", False)
        else:
            self.ui.rec_label.setProperty("active", True)

        update_element_styles(self.ui.rec_label)

    # Цей слот викликається з MainWindow, коли запис зупиняється
    def reset_state(self):
        self.setVisible(False)
        self.ui.pause_button.setChecked(False)
        self.update_duration("00:00:00")

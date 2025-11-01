from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSlot, QSize
from PyQt6.QtGui import QIcon
from PyQt6 import uic
import os

from app.ui.ui_record_status_widget import Ui_RecordingStatusWidget


class RecordingStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._load_ui()

        # --- Налаштування іконок (це все ще робиться в коді) ---
        self.pause_icon = QIcon("images/homeBtn_off.png")  # TODO: Вкажіть шлях
        self.resume_icon = QIcon("images/homeBtn_off.png")  # TODO: Вкажіть шлях

        # Встановлюємо іконку за замовчуванням
        self.pause_button.setIcon(self.pause_icon)

        # Підключаємо сигнал до слота, який вже є в цьому класі
        # self.pause_button.toggled.connect(self.on_pause_toggled) # Це вже зроблено у MainWindow

        # Схований по замовчуванню
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
        # self.duration_label - це ім'я (name) віджета з .ui файлу
        self.duration_label.setText(time_str)

    @pyqtSlot(bool)
    def on_pause_toggled(self, is_paused):
        # Оновлюємо іконку кнопки
        if is_paused:
            self.pause_button.setIcon(self.resume_icon)
            self.rec_label.setText("⏸️")  # Міняємо іконку статусу
        else:
            self.pause_button.setIcon(self.pause_icon)
            self.rec_label.setText("🔴")

    # Цей слот викликається з MainWindow, коли запис зупиняється
    def reset_state(self):
        self.setVisible(False)
        self.pause_button.setChecked(False)  # "Віджати" кнопку
        self.update_duration("00:00:00")

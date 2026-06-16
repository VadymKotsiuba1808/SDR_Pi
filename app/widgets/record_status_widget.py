"""
Віджет статусу запису.
Показує індикатор (червона крапка/таймер), коли йде запис екрану.
"""

from typing import Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.ui.ui_record_status_widget import Ui_RecordingStatusWidget
from app.utils.ui_utils import update_element_styles


class RecordingStatusWidget(QWidget):
    """
    Віджет статусу запису екрану.

    Малий плаваючий індикатор, який відображає поточну тривалість запису
    та стан (Запис/Пауза). Керується через `RecordingService`.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._load_ui()
        self.setVisible(False)

    def _load_ui(self) -> None:
        """Завантажує UI шаблон."""
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_RecordingStatusWidget()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/record_status_widget.ui", self)
            self.ui = cast(Ui_RecordingStatusWidget, self)

    @pyqtSlot(str)
    def update_duration(self, time_str: str) -> None:
        """Оновлює текстове значення таймера."""
        self.ui.duration_label.setText(time_str)

    @pyqtSlot(bool)
    def on_pause_toggled(self, is_paused: bool) -> None:
        """Змінює візуальний стан індикатора при паузі."""
        # Змінюємо властивість для активації QSS стилів (наприклад, колір крапки)
        self.ui.rec_label.setProperty("active", not is_paused)
        update_element_styles(self.ui.rec_label)

    def reset_state(self) -> None:
        """Скидає стан віджета до початкового."""
        self.setVisible(False)
        self.ui.pause_button.setChecked(False)
        self.update_duration("00:00:00")

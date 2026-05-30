from typing import Optional

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTranslator, pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QDialog, QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.protocols import LangSettings
from app.services.pi_network_service import PiNetworkService
from app.ui.ui_chart_monitor_dialog import Ui_ChartMonitorDialog
from app.widgets.dynamic_chart_widget import DynamicChartWidget


class ChartMonitorDialog(QDialog):
    """
    Діалог моніторингу сигналів у реальному часі.
    Керує потоком даних від NetworkService до DynamicChartWidget.
    """

    def __init__(
        self,
        network_service: PiNetworkService,
        settings_service: LangSettings,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.network_service = network_service
        self.settings_service = settings_service

        self._load_ui()
        self._setup_variables()
        self._init_chart_widget()
        self._connect_handlers()

        self.chart_widget.set_hover_enabled(self.is_paused)

        print("[Monitor] Dialog initialized.")

        self._load_language()
        self._start_stream_for_current_source()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                print("[Settings] Language change detected, retranslating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_ChartMonitorDialog()
            self.ui.setupUi(self)
            pass
        else:
            uic.loadUi("app/ui/realtime_monitor.ui", self)
            self.ui = self

    def _setup_variables(self):
        self.translator = QTranslator()
        self.chart_widget: Optional[DynamicChartWidget] = None

        self.stream_type = SourceType.RF

        combo_idx = self.ui.comboSource.currentIndex()
        if combo_idx == 1:
            self.stream_type = SourceType.SOUND

        self.is_paused = False

    def _init_chart_widget(self) -> None:
        self.chart_widget = DynamicChartWidget()

        self.ui.chartContainerLayout.addWidget(self.chart_widget)

    def _connect_handlers(self) -> None:
        self.ui.comboSource.currentIndexChanged.connect(self._handle_source_change)
        self.ui.comboChart.currentTextChanged.connect(self._handle_chart_mode_change)
        self.ui.btnPause.toggled.connect(self._handle_pause_toggle)
        self.ui.btnClose.clicked.connect(self.close)
        self.ui.btnResetZoom.clicked.connect(self._handle_reset_zoom)

        self.network_service.rf_data_received.connect(self._on_stream_data)
        self.network_service.sound_data_received.connect(self._on_stream_data)

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

    def _change_source(self, idx):
        if idx == 1:
            self.stream_type = SourceType.SOUND
        else:
            self.stream_type = SourceType.RF

    def _handle_source_change(self, index) -> None:
        """Зміна джерела (RF <-> Sound)."""
        self._change_source(index)

        if not self.is_paused:
            self._start_stream_for_current_source()
            self._handle_clear_charts()
            self._handle_reset_zoom()

    def _handle_clear_charts(self):
        if self.chart_widget:
            self.chart_widget.clear_charts()

    def _handle_reset_zoom(self):
        if self.chart_widget:
            self.chart_widget.reset_view()

    def _handle_chart_mode_change(self, text: str) -> None:
        """Зміна видимості графіків (Спектр / Водоспад)."""
        if "Spectrum" in text:
            mode = "Spectrum"
        elif "Waterfall" in text:
            mode = "Waterfall"
        else:
            mode = "Both"

        if self.chart_widget:
            self.chart_widget.set_view_mode(mode)

    def _handle_pause_toggle(self, is_paused: bool) -> None:
        """Обробка кнопки Пауза."""
        if self.chart_widget:
            self.chart_widget.set_hover_enabled(is_paused)

        self.is_paused = is_paused

        if is_paused:
            print("[Monitor] Pausing stream...")
        else:
            print("[Monitor] Resuming stream...")
            self._start_stream_for_current_source()

    def _start_stream_for_current_source(self):
        """Допоміжний метод для запуску потоку."""

        if self.stream_type == SourceType.SOUND:
            self.network_service.request_rf_data_end()
            self.network_service.request_sound_data_start()
        else:
            self.network_service.request_sound_data_end()
            self.network_service.request_rf_data_start()

        print(
            f"[Monitor] Mock: NetworkService.start_realtime_stream({self.stream_type})"
        )

    @pyqtSlot(object)
    def _on_stream_data(self, chunk: StreamDataChunk) -> None:
        if self.is_paused:
            return

        if chunk.stream_type != self.stream_type:
            return

        if self.chart_widget:
            self.chart_widget.update_data(chunk)

    def closeEvent(self, event: QCloseEvent) -> None:
        print("[Monitor] Closing dialog, stopping stream...")

        if self.is_paused:
            return

        if self.stream_type == SourceType.RF:
            self.network_service.request_rf_data_end()
        else:
            self.network_service.request_sound_data_end()

        event.accept()

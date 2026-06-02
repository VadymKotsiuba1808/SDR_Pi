from typing import Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTranslator, pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QDialog, QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.core.logging_config import get_logger
from app.core.mixins import TestUIOptimizationMixin
from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.protocols import LangSettings
from app.services.pi_network_service import PiNetworkService
from app.ui.ui_chart_monitor_dialog import Ui_ChartMonitorDialog
from app.widgets.dynamic_chart_widget import DynamicChartWidget

logger = get_logger(__name__)


class ChartMonitorDialog(QDialog, TestUIOptimizationMixin):
    """
    ### Діалог моніторингу сигналів
    Візуалізує спектральні дані від `PiNetworkService` через `DynamicChartWidget`.

    **Особливості:**
    - Безрамкове вікно для оптимізації простору на сенсорних екранах.
    - Підтримка RF та SOUND джерел даних.
    - Динамічне перемикання мови без перезапуску.
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

        if self.chart_widget is not None:
            self.chart_widget.set_hover_enabled(self.is_paused)

        self._load_language()
        self._start_stream_for_current_source()
        self.apply_test_ui_optimization()

    def changeEvent(self, a0: QEvent | None) -> None:
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_ChartMonitorDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/realtime_monitor.ui", self)
            self.ui = cast(Ui_ChartMonitorDialog, self)

    def _setup_variables(self) -> None:
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
        """Завантажує файл перекладу згідно з налаштуваннями."""
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)
        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)

    def _change_source(self, idx: int) -> None:
        self.stream_type = SourceType.SOUND if idx == 1 else SourceType.RF

    def _handle_source_change(self, index: int) -> None:
        """Обробник зміни джерела (RF <-> Sound)."""
        self._change_source(index)
        logger.info(f"Зміна джерела даних на: {self.stream_type}")

        if not self.is_paused:
            self._start_stream_for_current_source()
            self._handle_clear_charts()
            self._handle_reset_zoom()

    def _handle_clear_charts(self) -> None:
        if self.chart_widget:
            self.chart_widget.clear_charts()

    def _handle_reset_zoom(self) -> None:
        if self.chart_widget:
            self.chart_widget.reset_view()

    def _handle_chart_mode_change(self, text: str) -> None:
        """Зміна видимості графіків (Спектр/Водоспад/Обидва)."""
        if "Spectrum" in text:
            mode = "Spectrum"
        elif "Waterfall" in text:
            mode = "Waterfall"
        else:
            mode = "Both"

        if self.chart_widget:
            self.chart_widget.set_view_mode(mode)

    def _handle_pause_toggle(self, is_paused: bool) -> None:
        """Обробка натискання кнопки паузи."""
        if self.chart_widget:
            self.chart_widget.set_hover_enabled(is_paused)

        self.is_paused = is_paused
        logger.info(f"Пауза моніторингу: {is_paused}")

        if not is_paused:
            self._start_stream_for_current_source()

    def _start_stream_for_current_source(self) -> None:
        """Запускає потік RAW-даних для вибраного джерела."""
        logger.debug(f"Запит на запуск потоку: {self.stream_type}")
        if self.stream_type == SourceType.SOUND:
            self.network_service.request_rf_data_end()
            self.network_service.request_sound_data_start()
        else:
            self.network_service.request_sound_data_end()
            self.network_service.request_rf_data_start()

    @pyqtSlot(object)
    def _on_stream_data(self, chunk: StreamDataChunk) -> None:
        """Отримує та відображає чанки даних."""
        if self.is_paused or chunk.stream_type != self.stream_type:
            return

        if self.chart_widget:
            self.chart_widget.update_data(chunk)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Зупиняє потоки даних при закритті вікна."""
        logger.info("Закриття діалогу моніторингу")
        event = a0

        if not self.is_paused:
            if self.stream_type == SourceType.RF:
                self.network_service.request_rf_data_end()
            else:
                self.network_service.request_sound_data_end()

        if event:
            event.accept()

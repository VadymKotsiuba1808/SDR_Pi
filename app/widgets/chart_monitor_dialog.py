from typing import Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTranslator, pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QDialog, QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.core.mixins import TestUIOptimizationMixin
from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.protocols import LangSettings
from app.services.pi_network_service import PiNetworkService
from app.ui.ui_chart_monitor_dialog import Ui_ChartMonitorDialog
from app.widgets.dynamic_chart_widget import DynamicChartWidget


class ChartMonitorDialog(QDialog, TestUIOptimizationMixin):
    """
    Діалог моніторингу сигналів у реальному часі.

    Виконує роль контролера для візуалізації спектральних даних.
    Координує потік даних від `PiNetworkService` (мережевий рівень)
    до `DynamicChartWidget` (графічний рівень).
    """

    def __init__(
        self,
        network_service: PiNetworkService,
        settings_service: LangSettings,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Ініціалізує діалог та налаштовує віджети графіків.

        !!! info "Дизайн інтерфейсу"
            Встановлюється прапорець `FramelessWindowHint`, оскільки додаток розрахований
            на роботу з сенсорним екраном Raspberry Pi, де стандартні рамки вікон
            займають забагато корисного простору та заважають керуванню.

        Args:
            network_service (PiNetworkService): Сервіс для отримання потокових даних з Raspberry Pi.
            settings_service (LangSettings): Сервіс доступу до налаштувань (мова, параметри).
            parent (Optional[QWidget], optional): Батьківський віджет. За замовчуванням None.
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.network_service = network_service
        self.settings_service = settings_service

        self._load_ui()
        self._setup_variables()
        self._init_chart_widget()
        self._connect_handlers()

        # Дозволяємо перегляд значень на графіку, якщо потік на паузі
        if self.chart_widget is not None:
            self.chart_widget.set_hover_enabled(self.is_paused)

        self._load_language()
        # Автоматичний запуск потоку даних при відкритті вікна для негайного фідбеку користувачу
        self._start_stream_for_current_source()
        self.apply_test_ui_optimization()

    def changeEvent(self, a0: QEvent | None) -> None:
        """
        Обробник системних подій.

        Використовується переважно для динамічного оновлення інтерфейсу при зміні мови
        без необхідності перезапуску діалогу.

        Args:
            a0 (QEvent | None): Подія, що надійшла від системи.
        """
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        """
        Завантажує UI компоненти.

        Підтримує як скомпільовані Python-класи UI, так і динамічне завантаження .ui файлів,
        що зручно для швидкої ітерації під час розробки.
        """
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_ChartMonitorDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/realtime_monitor.ui", self)
            self.ui = cast(Ui_ChartMonitorDialog, self)

    def _setup_variables(self) -> None:
        """
        Ініціалізує внутрішні змінні стану діалогу.

        Встановлює початковий тип джерела даних на основі поточного вибору в комбобоксі.
        """
        self.translator = QTranslator()
        self.chart_widget: Optional[DynamicChartWidget] = None

        # Тип потоку за замовчуванням - Радіочастоти (RF)
        self.stream_type = SourceType.RF

        combo_idx = self.ui.comboSource.currentIndex()
        if combo_idx == 1:
            self.stream_type = SourceType.SOUND

        self.is_paused = False

    def _init_chart_widget(self) -> None:
        """
        Створює та інтегрує віджет динамічних графіків у макет.

        Використовує `DynamicChartWidget` для абстракції логіки малювання спектра та водоспаду.
        """
        self.chart_widget = DynamicChartWidget()
        self.ui.chartContainerLayout.addWidget(self.chart_widget)

    def _connect_handlers(self) -> None:
        """
        Підключає сигнали елементів UI та мережевого сервісу до обробників.

        !!! note "Потокові дані"
            Підписка відбувається на обидва типи даних (RF та Sound), але метод `_on_stream_data`
            фільтрує їх за поточним активним `stream_type`.
        """
        self.ui.comboSource.currentIndexChanged.connect(self._handle_source_change)
        self.ui.comboChart.currentTextChanged.connect(self._handle_chart_mode_change)
        self.ui.btnPause.toggled.connect(self._handle_pause_toggle)
        self.ui.btnClose.clicked.connect(self.close)
        self.ui.btnResetZoom.clicked.connect(self._handle_reset_zoom)

        self.network_service.rf_data_received.connect(self._on_stream_data)
        self.network_service.sound_data_received.connect(self._on_stream_data)

    def _load_language(self) -> None:
        """
        Завантажує файл перекладу відповідно до налаштувань користувача.

        !!! warning "Керування транслятором"
            Важливо видалити старий транслятор перед встановленням нового, щоб уникнути
            накладання декількох мовних файлів у пам'яті.
        """
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)
        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)

    def _change_source(self, idx: int) -> None:
        """
        Внутрішній метод перемикання типу джерела.

        Args:
            idx (int): Індекс вибраного елемента в комбобоксі джерел.
        """
        self.stream_type = SourceType.SOUND if idx == 1 else SourceType.RF

    def _handle_source_change(self, index: int) -> None:
        """
        Обробник зміни джерела (RF <-> Sound).

        При зміні джерела старий потік зупиняється, графіки очищуються,
        і ініціюється запит на отримання нових даних.

        Args:
            index (int): Новий індекс джерела.
        """
        self._change_source(index)

        if not self.is_paused:
            self._start_stream_for_current_source()
            self._handle_clear_charts()
            self._handle_reset_zoom()

    def _handle_clear_charts(self) -> None:
        """Очищує історію водоспаду та лінію спектра."""
        if self.chart_widget:
            self.chart_widget.clear_charts()

    def _handle_reset_zoom(self) -> None:
        """Скидає масштаб графіків до стандартного виду."""
        if self.chart_widget:
            self.chart_widget.reset_view()

    def _handle_chart_mode_change(self, text: str) -> None:
        """
        Зміна видимості графіків (Спектр / Водоспад / Обидва).

        !!! info "Архітектурне рішення"
            Віджет DynamicChartWidget завжди отримує дані, але режим 'view_mode'
            керує виключно візуальною частиною (hide/show віджетів), що економить CPU.
        """
        if "Spectrum" in text:
            mode = "Spectrum"
        elif "Waterfall" in text:
            mode = "Waterfall"
        else:
            mode = "Both"

        if self.chart_widget:
            self.chart_widget.set_view_mode(mode)

    def _handle_pause_toggle(self, is_paused: bool) -> None:
        """
        Обробка натискання кнопки паузи.

        Призупиняє візуальне оновлення графіків, але дозволяє інтерактивну
        взаємодію (Hover) для аналізу спектра на зафіксованому кадрі.

        Args:
            is_paused (bool): Стан кнопки (True - пауза активована).
        """
        if self.chart_widget:
            self.chart_widget.set_hover_enabled(is_paused)

        self.is_paused = is_paused

        if not is_paused:
            self._start_stream_for_current_source()

    def _start_stream_for_current_source(self) -> None:
        """
        Надсилає мережевий запит на сервер для початку трансляції RAW-даних.

        Перед активацією нового потоку обов'язково зупиняє попередній, щоб уникнути
        перевантаження мережевого каналу між Raspberry Pi та ПК.
        """
        if self.stream_type == SourceType.SOUND:
            self.network_service.request_rf_data_end()
            self.network_service.request_sound_data_start()
        else:
            self.network_service.request_sound_data_end()
            self.network_service.request_rf_data_start()

    @pyqtSlot(object)
    def _on_stream_data(self, chunk: StreamDataChunk) -> None:
        """
        Основний слот отримання чанків даних.

        Виконує фільтрацію за типом джерела, щоб запобігти відображенню застарілих даних
        або даних з іншого каналу під час перемикання джерел.

        Args:
            chunk (StreamDataChunk): Дані спектра (частоти, потужності, метадані).
        """
        if self.is_paused:
            return

        if chunk.stream_type != self.stream_type:
            return

        if self.chart_widget:
            self.chart_widget.update_data(chunk)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """
        Обробник події закриття діалогу.

        !!! info "Економія ресурсів"
            При закритті вікна обов'язково надсилається команда на зупинку потоку даних.
            Це критично важливо для Raspberry Pi, оскільки генерація та передача RAW-спектра
            споживає значні ресурси CPU та пропускну здатність мережі.

        Args:
            a0 (QCloseEvent | None): Подія закриття.
        """
        event = a0

        if not self.is_paused:
            if self.stream_type == SourceType.RF:
                self.network_service.request_rf_data_end()
            else:
                self.network_service.request_sound_data_end()

        if event:
            event.accept()

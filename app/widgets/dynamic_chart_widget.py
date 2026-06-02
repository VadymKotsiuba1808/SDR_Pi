from typing import Final, Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from app.core.chart_theme import ChartTheme
from app.core.constants import (
    DB_OFFSET,
    UINT8_MAX,
    VISUAL_MIN_DB,
    VISUAL_NOISE_FLOOR_UINT8,
)
from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.ui.components.chart_crosshair import PyGraphCrosshair


class DynamicChartWidget(QWidget):
    """
    ### DynamicChartWidget
    Віджет для відображення спектру та водоспаду в реальному часі.

    Використовує бібліотеку `pyqtgraph` для високоефективної візуалізації
    великих масивів даних FFT. Підтримує динамічне перемикання між
    радіочастотним (RF) та акустичним (SOUND) діапазонами.
    """

    # Константи візуалізації
    DEFAULT_HISTORY: Final[int] = 200  # Кількість рядків у водоспаді (глибина історії)
    DEFAULT_FFT: Final[int] = 512  # Базовий розмір вікна швидкого перетворення Фур'є

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Ініціалізує графічне ядро та буфери даних."""
        super().__init__(parent)

        self._init_global_config()
        self._setup_ui()
        self._setup_state_variables()
        self._setup_plots()
        self._connect_handlers()

        self.reset_view()

    def _init_global_config(self) -> None:
        pg.setConfigOption("background", ChartTheme.DYN_BACKGROUND)
        pg.setConfigOption("foreground", ChartTheme.DYN_FOREGROUND)
        pg.setConfigOptions(antialias=True)  # Згладжування ліній спектру

    def _setup_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # GraphicsLayoutWidget дозволяє розміщувати кілька графіків в одній сітці
        self.win = pg.GraphicsLayoutWidget()
        self.main_layout.addWidget(self.win)

    def _setup_state_variables(self) -> None:
        self.current_source_type: SourceType = SourceType.RF
        self.history_size: int = self.DEFAULT_HISTORY
        self.fft_size: int = self.DEFAULT_FFT

        self.freqs_cache: Optional[np.ndarray] = None
        self.is_hover_enabled: bool = True

        # Буфер водоспаду у форматі uint8 для економії відеопам'яті
        self.waterfall_buffer: np.ndarray = np.zeros(
            (self.history_size, self.fft_size), dtype=np.uint8
        )

    def _setup_plots(self) -> None:
        # --- 1. Спектр (Лінійний графік потужності) ---
        self.plot_spectrum: pg.PlotItem = self.win.addPlot(
            title=self.tr("Real-Time Spectrum")
        )
        self.plot_spectrum.showGrid(x=True, y=True, alpha=0.3)
        self.plot_spectrum.setLabel("left", self.tr("Amplitude"), units=self.tr("dB"))
        self.plot_spectrum.setYRange(VISUAL_MIN_DB, 0)

        self.spectrum_curve = self.plot_spectrum.plot(
            pen=pg.mkPen(ChartTheme.DYN_SPECTRUM_PEN, width=2)
        )
        self.cursor_spectrum = PyGraphCrosshair(self.plot_spectrum)

        self.win.nextRow()  # Перехід на наступний рядок у сітці графіків

        # --- 2. Водоспад (Кольорова історія сигналу в часі) ---
        self.plot_waterfall: pg.PlotItem = self.win.addPlot(
            title=self.tr("Waterfall History")
        )
        self.plot_waterfall.setLabel("left", self.tr("Time"), units=self.tr("scans"))

        self.img_item = pg.ImageItem()
        self.plot_waterfall.addItem(self.img_item)

        self._setup_colormap()
        self.cursor_waterfall = PyGraphCrosshair(self.plot_waterfall)

    def _setup_colormap(self) -> None:
        pos = np.array(ChartTheme.WATERFALL_POS)
        color = np.array(ChartTheme.WATERFALL_COLORS, dtype=np.ubyte)

        color_map = pg.ColorMap(pos, color)
        # Генеруємо 256 кольорів для відповідності 8-бітному буферу
        self.img_item.setLookupTable(color_map.getLookupTable(0.0, 1.0, 256))

    def _connect_handlers(self) -> None:
        scene = self.win.scene()
        if scene is not None:
            scene.sigMouseMoved.connect(self._on_mouse_moved)

    def clear_charts(self) -> None:
        """Повністю очищує графіки та зануляє буфери пам'яті."""
        self.waterfall_buffer.fill(0)
        self.img_item.setImage(
            self.waterfall_buffer.T,
            autoLevels=False,
            levels=(VISUAL_NOISE_FLOOR_UINT8, UINT8_MAX),
        )
        self.spectrum_curve.setData([], [])
        self.freqs_cache = None
        self.cursor_spectrum.hide()
        self.cursor_waterfall.hide()

    def update_data(self, chunk: StreamDataChunk) -> None:
        """Оновлює графіки новими даними FFT."""
        raw_data = chunk.data_magnitude
        current_len = len(raw_data)

        # Автоматична адаптація при зміні роздільної здатності FFT сервером
        if current_len != self.fft_size:
            self._handle_resize(current_len)

        # Розрахунок осі X (частоти)
        freqs = self._calculate_frequencies(chunk, current_len)
        self.freqs_cache = freqs

        # Перевід амплітуд у візуальний dB діапазон
        display_data_db = raw_data.astype(np.float32) - DB_OFFSET
        self.spectrum_curve.setData(freqs, display_data_db)

        # Оновлення водоспаду: зсув старого кадру вниз та запис нового вгору (axis 0)
        self.waterfall_buffer = np.roll(self.waterfall_buffer, 1, axis=0)
        self.waterfall_buffer[0] = raw_data

        # Передача транспонованого буфера в ImageItem (вимога pyqtgraph для осей X/Y)
        self.img_item.setImage(
            self.waterfall_buffer.T,
            autoLevels=False,
            levels=(VISUAL_NOISE_FLOOR_UINT8, UINT8_MAX),
        )

        # Масштабування картинки водоспаду під фізичні частоти
        if len(freqs) > 1:
            rect = [freqs[0], 0, freqs[-1] - freqs[0], self.history_size]
            self.img_item.setRect(rect)

    def set_hover_enabled(self, enabled: bool) -> None:
        """Керує видимістю інтерактивного перехрестя."""
        self.is_hover_enabled = enabled
        if not enabled:
            self.cursor_spectrum.hide()
            self.cursor_waterfall.hide()

    def reset_view(self) -> None:
        """Скидає межі графіків до початкового стану."""
        self.plot_spectrum.enableAutoRange()
        self.plot_waterfall.enableAutoRange()
        if self.freqs_cache is not None:
            self.plot_waterfall.setXRange(self.freqs_cache[0], self.freqs_cache[-1])
            self.plot_waterfall.setYRange(0, self.history_size)

    def set_view_mode(self, mode: str) -> None:
        """Перемикає видимість компонентів (Спектр / Водоспад / Обидва)."""
        mode = mode.lower()
        self.plot_spectrum.setVisible("spectrum" in mode or "both" in mode)
        self.plot_waterfall.setVisible("waterfall" in mode or "both" in mode)

    def _handle_resize(self, new_size: int) -> None:
        """Переініціалізує буфери при зміні розміру вхідних даних."""
        self.fft_size = new_size
        self.waterfall_buffer = np.zeros(
            (self.history_size, self.fft_size), dtype=np.uint8
        )
        self.img_item.resetTransform()

    def _calculate_frequencies(self, chunk: StreamDataChunk, size: int) -> np.ndarray:
        """Розраховує масив частот (вісь X) на основі параметрів сигналу."""
        if chunk.stream_type == SourceType.RF:
            # Обчислення полоси навколо центральної частоти (I/Q дані)
            start = (chunk.center_freq_hz - chunk.sample_rate_hz / 2) / 1e6
            end = (chunk.center_freq_hz + chunk.sample_rate_hz / 2) / 1e6

            if self.current_source_type != SourceType.RF or self.freqs_cache is None:
                self._update_axis_labels(self.tr("MHz"))
                self.current_source_type = SourceType.RF

            return np.linspace(start, end, size)
        else:
            # Для звуку частота завжди від 0 до Nyquist (SampleRate/2)
            start, end = 0, chunk.sample_rate_hz / 2

            if self.current_source_type != SourceType.SOUND or self.freqs_cache is None:
                self._update_axis_labels(self.tr("Hz"))
                self.current_source_type = SourceType.SOUND

            return np.linspace(start, end, size)

    def _update_axis_labels(self, unit: str) -> None:
        """Оновлює підписи осей при зміні типу джерела."""
        self.plot_spectrum.setLabel("bottom", self.tr("Frequency"), units=unit)
        self.plot_waterfall.setLabel("bottom", self.tr("Frequency"), units=unit)

    def _on_mouse_moved(self, pos: QPointF) -> None:
        """Обробник руху миші для оновлення координат Crosshair."""
        if not self.is_hover_enabled or self.freqs_cache is None:
            return

        # Визначаємо, в межах якого графіка знаходиться курсор
        if self.plot_spectrum.sceneBoundingRect().contains(pos):
            self.cursor_waterfall.hide()
            self._update_cursor(
                self.plot_spectrum, self.cursor_spectrum, pos, is_waterfall=False
            )

        elif self.plot_waterfall.sceneBoundingRect().contains(pos):
            self.cursor_spectrum.hide()
            self._update_cursor(
                self.plot_waterfall, self.cursor_waterfall, pos, is_waterfall=True
            )
        else:
            self.cursor_spectrum.hide()
            self.cursor_waterfall.hide()

    def _update_cursor(
        self,
        plot: pg.PlotItem,
        cursor: PyGraphCrosshair,
        scene_pos: QPointF,
        is_waterfall: bool,
    ) -> None:
        """Розраховує точні фізичні значення (Частота/Амплітуда) під курсором."""
        if plot.vb is None:
            return

        # Перевід координат сцени у координати графіка
        mouse_point = plot.vb.mapSceneToView(scene_pos)
        x_freq = mouse_point.x()
        y_val = mouse_point.y()

        idx = self._get_freq_index(x_freq)
        if idx is None:
            cursor.hide()
            return

        def get_amp_val(row: int, col: int) -> float:
            """Отримує амплітуду з буфера з врахуванням dB зсуву."""
            raw_val = self.waterfall_buffer[row][col]
            return float(raw_val) - DB_OFFSET

        if is_waterfall:
            row_idx = int(y_val)
            if 0 <= row_idx < self.history_size:
                real_amp = get_amp_val(row_idx, idx)
                text = self.tr("Freq: {:.3f}\nTime: {}\nAmp: {:.1f} dB").format(
                    x_freq, row_idx, real_amp
                )
                cursor.update_position(x_freq, y_val, text)
            else:
                cursor.hide()
        else:
            # На спектрі завжди показуємо амплітуду останнього (верхнього) кадру
            real_amp = get_amp_val(0, idx)
            text = self.tr("Freq: {:.3f}\nAmp: {:.1f} dB").format(x_freq, real_amp)
            cursor.update_position(x_freq, y_val, text)

    def _get_freq_index(self, freq_val: float) -> Optional[int]:
        """Знаходить індекс у масиві даних FFT, що відповідає частоті."""
        if self.freqs_cache is None:
            return None

        min_f, max_f = self.freqs_cache[0], self.freqs_cache[-1]
        if not (min_f <= freq_val <= max_f):
            return None

        # Проста лінійна інтерполяція для пошуку індексу
        fraction = (freq_val - min_f) / (max_f - min_f)
        idx = int(fraction * (len(self.freqs_cache) - 1))

        return idx if 0 <= idx < self.fft_size else None

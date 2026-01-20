import numpy as np
import pyqtgraph as pg
from typing import Optional, Final

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPointF

from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.core.chart_theme import ChartTheme

from app.ui.components.chart_crosshair import PyGraphCrosshair


class DynamicChartWidget(QWidget):
    """
    Віджет для відображення спектру та водоспаду в реальному часі (pyqtgraph).
    """

    DEFAULT_HISTORY: Final[int] = 200
    DEFAULT_FFT: Final[int] = 512

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._init_global_config()

        self._setup_ui()
        self._setup_state_variables()
        self._setup_plots()
        self._connect_handlers()

    def _init_global_config(self) -> None:
        """Налаштування глобальних параметрів pyqtgraph."""
        pg.setConfigOption("background", ChartTheme.DYN_BACKGROUND)
        pg.setConfigOption("foreground", ChartTheme.DYN_FOREGROUND)
        pg.setConfigOptions(antialias=True)

    def _setup_ui(self) -> None:
        """Створення базового лейауту."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.win = pg.GraphicsLayoutWidget()
        self.main_layout.addWidget(self.win)

    def _setup_state_variables(self) -> None:
        """Ініціалізація внутрішніх змінних стану."""
        self.current_source_type: SourceType = SourceType.RF
        self.history_size: int = self.DEFAULT_HISTORY
        self.fft_size: int = self.DEFAULT_FFT

        self.freqs_cache: Optional[np.ndarray] = None
        self.is_hover_enabled: bool = True

        self.waterfall_buffer: np.ndarray = np.zeros(
            (self.history_size, self.fft_size), dtype=np.float64
        )

    def _setup_plots(self) -> None:
        """Ініціалізація графіків Спектру та Водоспаду."""

        self.plot_spectrum: pg.PlotItem = self.win.addPlot(title="Real-Time Spectrum")
        self.plot_spectrum.showGrid(x=True, y=True, alpha=0.3)
        self.plot_spectrum.setLabel("left", "Amplitude", units="dB")

        self.spectrum_curve = self.plot_spectrum.plot(
            pen=pg.mkPen(ChartTheme.DYN_SPECTRUM_PEN, width=2)
        )
        self.cursor_spectrum = PyGraphCrosshair(self.plot_spectrum)

        self.win.nextRow()

        self.plot_waterfall: pg.PlotItem = self.win.addPlot(title="Waterfall History")
        self.plot_waterfall.setLabel("left", "Time", units="scans")

        self.img_item = pg.ImageItem()
        self.plot_waterfall.addItem(self.img_item)

        self._setup_colormap()
        self.cursor_waterfall = PyGraphCrosshair(self.plot_waterfall)

    def _setup_colormap(self) -> None:
        """Налаштування палітри кольорів для водоспаду."""
        pos = np.array(ChartTheme.WATERFALL_POS)
        color = np.array(ChartTheme.WATERFALL_COLORS, dtype=np.ubyte)
        color_map = pg.ColorMap(pos, color)
        self.img_item.setLookupTable(color_map.getLookupTable(0.0, 1.0, 256))

    def _connect_handlers(self) -> None:
        """Підключення подій миші."""
        self.win.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def update_data(self, chunk: StreamDataChunk) -> None:
        """Оновлює графіки новими даними з потоку."""
        data = chunk.data_magnitude
        current_len = len(data)

        if current_len != self.fft_size:
            self._handle_resize(current_len)

        freqs = self._calculate_frequencies(chunk, current_len)
        self.freqs_cache = freqs

        self.spectrum_curve.setData(freqs, data)

        self.waterfall_buffer = np.roll(self.waterfall_buffer, 1, axis=0)
        self.waterfall_buffer[0] = data

        self.img_item.setImage(
            self.waterfall_buffer.T, autoLevels=False, levels=(0, 100)
        )

        if len(freqs) > 1:
            rect = [freqs[0], 0, freqs[-1] - freqs[0], self.history_size]
            self.img_item.setRect(rect)

    def set_hover_enabled(self, enabled: bool) -> None:
        self.is_hover_enabled = enabled
        if not enabled:
            self.cursor_spectrum.hide()
            self.cursor_waterfall.hide()

    def reset_view(self) -> None:
        """Скидає зум до початкового стану."""
        self.plot_spectrum.enableAutoRange()
        self.plot_waterfall.enableAutoRange()
        if self.freqs_cache is not None:
            self.plot_waterfall.setXRange(self.freqs_cache[0], self.freqs_cache[-1])
            self.plot_waterfall.setYRange(0, self.history_size)

    def set_view_mode(self, mode: str) -> None:
        """Перемикає видимість графіків (Spectrum / Waterfall / Both)."""
        mode = mode.lower()
        self.plot_spectrum.setVisible("spectrum" in mode or "both" in mode)
        self.plot_waterfall.setVisible("waterfall" in mode or "both" in mode)

    def _handle_resize(self, new_size: int) -> None:
        self.fft_size = new_size
        self.waterfall_buffer = np.zeros((self.history_size, self.fft_size))
        self.img_item.resetTransform()

    def _calculate_frequencies(self, chunk: StreamDataChunk, size: int) -> np.ndarray:
        """Розрахунок масиву частот залежно від типу джерела (RF/Audio)."""
        if chunk.stream_type == SourceType.RF:
            start = (chunk.center_freq - chunk.sample_rate / 2) / 1e6
            end = (chunk.center_freq + chunk.sample_rate / 2) / 1e6

            if self.current_source_type != SourceType.RF or self.freqs_cache is None:
                self._update_axis_labels("MHz")
                self.current_source_type = SourceType.RF

            return np.linspace(start, end, size)
        else:
            start, end = 0, chunk.sample_rate / 2

            if self.current_source_type != SourceType.SOUND or self.freqs_cache is None:
                self._update_axis_labels("Hz")
                self.current_source_type = SourceType.SOUND

            return np.linspace(start, end, size)

    def _update_axis_labels(self, unit: str) -> None:
        self.plot_spectrum.setLabel("bottom", "Frequency", units=unit)
        self.plot_waterfall.setLabel("bottom", "Frequency", units=unit)

    def _on_mouse_moved(self, pos: QPointF) -> None:
        """Обробник руху миші для оновлення курсорів."""
        if not self.is_hover_enabled or self.freqs_cache is None:
            return

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
        mouse_point = plot.vb.mapSceneToView(scene_pos)
        x_freq = mouse_point.x()
        y_val = mouse_point.y()

        idx = self._get_freq_index(x_freq)
        if idx is None:
            cursor.hide()
            return

        if is_waterfall:
            row_idx = int(y_val)
            if 0 <= row_idx < self.history_size:
                amp = self.waterfall_buffer[row_idx][idx]
                text = f"Freq: {x_freq:.3f}\nTime: {row_idx}\nAmp: {amp:.1f} dB"
                cursor.update_position(x_freq, y_val, text)
            else:
                cursor.hide()
        else:
            amp = self.waterfall_buffer[0][idx]
            text = f"Freq: {x_freq:.3f}\nAmp: {amp:.1f} dB"
            cursor.update_position(x_freq, y_val, text)

    def _get_freq_index(self, freq_val: float) -> Optional[int]:
        """Конвертує значення частоти в індекс масиву."""
        if self.freqs_cache is None:
            return None

        min_f, max_f = self.freqs_cache[0], self.freqs_cache[-1]

        if not (min_f <= freq_val <= max_f):
            return None

        fraction = (freq_val - min_f) / (max_f - min_f)
        idx = int(fraction * (len(self.freqs_cache) - 1))

        return idx if 0 <= idx < self.fft_size else None

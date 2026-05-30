"""
Тести для віджета динамічних графіків (DynamicChartWidget).
"""

import numpy as np
import pytest

from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.widgets.dynamic_chart_widget import DynamicChartWidget


@pytest.fixture
def dynamic_chart(qtbot):
    """Фікстура для ініціалізації DynamicChartWidget."""
    widget = DynamicChartWidget()
    qtbot.addWidget(widget)
    return widget


def test_initial_state(dynamic_chart):
    """Тест початкового стану віджета."""
    assert dynamic_chart.history_size == DynamicChartWidget.DEFAULT_HISTORY
    assert dynamic_chart.fft_size == DynamicChartWidget.DEFAULT_FFT
    assert dynamic_chart.waterfall_buffer.shape == (200, 512)
    assert dynamic_chart.current_source_type == SourceType.RF


def test_update_data_rf(dynamic_chart):
    """Тест оновлення даних для RF сигналу."""
    data = np.random.randint(0, 255, 512, dtype=np.uint8)
    chunk = StreamDataChunk(
        stream_type=SourceType.RF,
        center_freq_hz=915_000_000.0,
        sample_rate_hz=10_000_000.0,
        data_magnitude=data,
        timestamp=123456789.0,
    )

    dynamic_chart.update_data(chunk)

    # Перевіряємо, що спектр оновився
    x, y = dynamic_chart.spectrum_curve.getData()
    assert len(x) == 512
    assert x[0] == 910.0  # 915 - 10/2
    assert x[-1] == 920.0  # 915 + 10/2

    # Перевіряємо водоспад
    assert np.array_equal(dynamic_chart.waterfall_buffer[0], data)


def test_handle_resize(dynamic_chart):
    """Тест автоматичної зміни розміру буфера при зміні FFT."""
    data = np.random.randint(0, 255, 1024, dtype=np.uint8)
    chunk = StreamDataChunk(
        stream_type=SourceType.RF,
        center_freq_hz=433_000_000.0,
        sample_rate_hz=2_000_000.0,
        data_magnitude=data,
        timestamp=0.0,
    )

    dynamic_chart.update_data(chunk)

    assert dynamic_chart.fft_size == 1024
    assert dynamic_chart.waterfall_buffer.shape == (200, 1024)


def test_clear_charts(dynamic_chart):
    """Тест очищення графіків."""
    data = np.random.randint(0, 255, 512, dtype=np.uint8)
    chunk = StreamDataChunk(
        stream_type=SourceType.RF,
        center_freq_hz=915e6,
        sample_rate_hz=10e6,
        data_magnitude=data,
        timestamp=0.0,
    )
    dynamic_chart.update_data(chunk)

    dynamic_chart.clear_charts()

    assert np.all(dynamic_chart.waterfall_buffer == 0)
    x, y = dynamic_chart.spectrum_curve.getData()
    assert x is None or len(x) == 0


def test_view_modes(dynamic_chart):
    """Тест перемикання режимів відображення."""
    dynamic_chart.set_view_mode("spectrum")
    assert dynamic_chart.plot_spectrum.isVisible()
    assert not dynamic_chart.plot_waterfall.isVisible()

    dynamic_chart.set_view_mode("waterfall")
    assert not dynamic_chart.plot_spectrum.isVisible()
    assert dynamic_chart.plot_waterfall.isVisible()

    dynamic_chart.set_view_mode("both")
    assert dynamic_chart.plot_spectrum.isVisible()
    assert dynamic_chart.plot_waterfall.isVisible()

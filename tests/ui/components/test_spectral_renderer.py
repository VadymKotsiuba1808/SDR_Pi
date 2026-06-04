"""Модуль містить тести для компонента візуалізації спектральних даних (SpectralRenderer)."""

import numpy as np
import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap

from app.models.detection_background import SpectralData
from app.ui.components.spectral_renderer import SpectralChartRenderer


@pytest.fixture
def spectral_renderer() -> SpectralChartRenderer:
    return SpectralChartRenderer()


def test_spectral_renderer_render_spectrum_no_bg(
    qapp, spectral_renderer: SpectralChartRenderer
) -> None:
    """Перевіряє рендеринг спектру за відсутності вхідних даних."""
    img = QPixmap(400, 300)
    painter = QPainter(img)
    rect = QRect(0, 0, 400, 300)

    # Перевіряємо, що виклик методу без даних не призводить до винятків
    spectral_renderer.render_spectrum(painter, rect, None)
    painter.end()


def test_spectral_renderer_calculate_cursor(
    spectral_renderer: SpectralChartRenderer,
) -> None:
    """Перевіряє правильність розрахунку параметрів курсору на графіку."""
    rect = QRect(0, 0, 1000, 500)
    bg = SpectralData(
        center_freq_hz=100e6,
        sample_rate_hz=20e6,
        duration_sec=5.0,
        data_magnitude=np.full(100, 100, dtype=np.uint8),
    )

    # Імітуємо клік користувача точно по центру області малювання для перевірки розрахунку частоти
    pos = QPoint(500, 250)
    state = spectral_renderer.calculate_cursor(pos, rect, bg, "spectrum")

    assert state.visible is True, "Cursor should be visible on valid click"
    assert "100.000" in state.text, "Cursor text should contain center frequency"
    assert state.highlight_point is not None, "Highlight point should be calculated"


def test_spectral_renderer_prepare_cache(
    qapp, spectral_renderer: SpectralChartRenderer
) -> None:
    """Перевіряє механізм кешування теплової карти (heatmap)."""
    # Створюємо тестову 2D матрицю для імітації спектральних накопичених даних
    matrix = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
    bg = SpectralData(
        center_freq_hz=0, sample_rate_hz=0, duration_sec=0, data_magnitude=matrix
    )

    spectral_renderer.prepare_cache(bg)
    assert spectral_renderer.cached_heatmap is not None, (
        "Heatmap cache should be created"
    )
    assert spectral_renderer.cached_heatmap.width() == 10, (
        "Cached image width should match input data"
    )

"""
Тести для компонентів рендерингу (SpectralRenderer).
"""

import numpy as np
import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap

from app.models.detection_background import SpectralData
from app.ui.components.spectral_renderer import SpectralChartRenderer


@pytest.fixture
def spectral_renderer():
    return SpectralChartRenderer()


def test_spectral_renderer_render_spectrum_no_bg(spectral_renderer):
    """Тест малювання спектру без даних (має бути заглушка)."""
    img = QPixmap(400, 300)
    painter = QPainter(img)
    rect = QRect(0, 0, 400, 300)

    spectral_renderer.render_spectrum(painter, rect, None)
    painter.end()
    # Якщо не впало - добре


def test_spectral_renderer_calculate_cursor(spectral_renderer):
    """Тест розрахунку положення курсору."""
    rect = QRect(0, 0, 1000, 500)
    bg = SpectralData(
        center_freq_hz=100e6,
        sample_rate_hz=20e6,
        duration_sec=5.0,
        data_magnitude=np.full(100, 100, dtype=np.uint8),
    )

    # Клік рівно посередині (500, 250)
    pos = QPoint(500, 250)
    state = spectral_renderer.calculate_cursor(pos, rect, bg, "spectrum")

    assert state.visible is True
    # Центральна частота 100 MHz
    assert "100.000" in state.text
    assert state.highlight_point is not None


def test_spectral_renderer_prepare_cache(spectral_renderer):
    """Тест кешування heatmap."""
    # 2D дані
    matrix = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
    bg = SpectralData(
        center_freq_hz=0, sample_rate_hz=0, duration_sec=0, data_magnitude=matrix
    )

    spectral_renderer.prepare_cache(bg)
    assert spectral_renderer.cached_heatmap is not None
    assert spectral_renderer.cached_heatmap.width() == 10

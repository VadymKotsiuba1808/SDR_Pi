"""
Тести для діалогу моніторингу графіків (ChartMonitorDialog).
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtCore import Qt

from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.widgets.chart_monitor_dialog import ChartMonitorDialog


@pytest.fixture
def mock_network():
    return MagicMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def monitor_dialog(qtbot, mock_network, mock_settings):
    """Фікстура для ініціалізації ChartMonitorDialog."""
    dialog = ChartMonitorDialog(mock_network, mock_settings)
    qtbot.addWidget(dialog)
    yield dialog
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.removeTranslator(dialog.translator)


def test_initial_stream_request(qtbot, mock_network, mock_settings):
    """Тест того, що при старті запитується потік RF."""
    dialog = ChartMonitorDialog(mock_network, mock_settings)
    qtbot.addWidget(dialog)
    # Повинен зупинити звук і почати RF
    assert mock_network.request_rf_data_start.called
    assert mock_network.request_sound_data_end.called


def test_source_switching(monitor_dialog, mock_network):
    """Тест перемикання джерела сигналу (RF <-> Sound)."""
    mock_network.reset_mock()

    # Перемикаємо на Sound (індекс 1)
    monitor_dialog.ui.comboSource.setCurrentIndex(1)

    assert monitor_dialog.stream_type == SourceType.SOUND
    assert mock_network.request_sound_data_start.called
    assert mock_network.request_rf_data_end.called


def test_pause_toggle(monitor_dialog, mock_network, qtbot):
    """Тест роботи кнопки паузи."""
    mock_network.reset_mock()

    # Вмикаємо паузу
    qtbot.mouseClick(monitor_dialog.ui.btnPause, Qt.MouseButton.LeftButton)
    assert monitor_dialog.is_paused is True

    # Імітуємо прихід даних під час паузи
    chunk = StreamDataChunk(
        stream_type=SourceType.RF,
        data_magnitude=np.zeros(512, dtype=np.uint8),
        center_freq_hz=0,
        sample_rate_hz=0,
        timestamp=0,
    )
    with patch.object(monitor_dialog.chart_widget, "update_data") as mock_update:
        monitor_dialog._on_stream_data(chunk)
        assert not mock_update.called

    # Вимикаємо паузу
    qtbot.mouseClick(monitor_dialog.ui.btnPause, Qt.MouseButton.LeftButton)
    assert monitor_dialog.is_paused is False
    assert mock_network.request_rf_data_start.called


def test_data_forwarding(monitor_dialog, qtbot):
    """Тест передачі даних до віджета графіка."""
    chunk = StreamDataChunk(
        stream_type=SourceType.RF,
        data_magnitude=np.array([10, 20, 30], dtype=np.uint8),
        center_freq_hz=915e6,
        sample_rate_hz=10e6,
        timestamp=123.456,
    )

    with patch.object(monitor_dialog.chart_widget, "update_data") as mock_update:
        # Викликаємо слот безпосередньо, оскільки network_service - це мок
        monitor_dialog._on_stream_data(chunk)
        mock_update.assert_called_once_with(chunk)


def test_close_stops_stream(monitor_dialog, mock_network):
    """Тест зупинки потоку при закритті діалогу."""
    mock_network.reset_mock()
    monitor_dialog.close()

    # Оскільки за замовчуванням RF, має зупинити RF
    assert mock_network.request_rf_data_end.called


def test_chart_mode_change(monitor_dialog):
    """Тест зміни режиму відображення (Спектр/Водоспад)."""
    with patch.object(monitor_dialog.chart_widget, "set_view_mode") as mock_mode:
        # Викликаємо обробник зміни режиму безпосередньо
        monitor_dialog._handle_chart_mode_change("Spectrum Only")
        mock_mode.assert_called_with("Spectrum")

        monitor_dialog._handle_chart_mode_change("Waterfall Only")
        mock_mode.assert_called_with("Waterfall")

        monitor_dialog._handle_chart_mode_change("Both")
        mock_mode.assert_called_with("Both")

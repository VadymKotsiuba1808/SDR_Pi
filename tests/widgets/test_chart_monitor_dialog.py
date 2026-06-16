"""Тести для віджета моніторингу графіків."""

from typing import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtCore import Qt

from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.widgets.chart_monitor_dialog import ChartMonitorDialog


@pytest.fixture
def mock_network() -> MagicMock:
    """Створює мок-об'єкт для мережевого сервісу."""
    return MagicMock()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Створює мок-об'єкт для сервісу налаштувань."""
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def monitor_dialog(
    qtbot, mock_network: MagicMock, mock_settings: MagicMock
) -> Generator[ChartMonitorDialog, None, None]:
    """Фікстура для ініціалізації ChartMonitorDialog."""
    dialog = ChartMonitorDialog(mock_network, mock_settings)
    qtbot.addWidget(dialog)
    yield dialog

    from PyQt6.QtCore import QCoreApplication

    # Важливо видалити транслятор, щоб він не впливав на інші тести
    QCoreApplication.removeTranslator(dialog.translator)


def test_initial_stream_request(
    qtbot, mock_network: MagicMock, mock_settings: MagicMock
) -> None:
    """Перевіряє автоматичний запуск запиту даних при відкритті діалогу."""
    dialog = ChartMonitorDialog(mock_network, mock_settings)
    qtbot.addWidget(dialog)

    assert mock_network.request_rf_data_start.called, (
        "RF data request should be started"
    )
    assert mock_network.request_sound_data_end.called, (
        "Sound data should be explicitly stopped"
    )


def test_source_switching(
    monitor_dialog: ChartMonitorDialog, mock_network: MagicMock
) -> None:
    """Перевіряє перемикання джерела сигналу через UI."""
    mock_network.reset_mock()

    # Перемикаємо на Sound (індекс 1 в comboSource)
    monitor_dialog.ui.comboSource.setCurrentIndex(1)

    assert monitor_dialog.stream_type == SourceType.SOUND, (
        "Stream type should change to SOUND"
    )
    assert mock_network.request_sound_data_start.called, (
        "Sound data request should be started"
    )
    assert mock_network.request_rf_data_end.called, "RF data request should be stopped"


def test_pause_toggle(
    monitor_dialog: ChartMonitorDialog, mock_network: MagicMock, qtbot
) -> None:
    """Перевіряє функціональність кнопки паузи."""
    mock_network.reset_mock()

    qtbot.mouseClick(monitor_dialog.ui.btnPause, Qt.MouseButton.LeftButton)
    assert monitor_dialog.is_paused is True, "Dialog should be in paused state"

    chunk = StreamDataChunk(
        stream_type=SourceType.RF,
        data_magnitude=np.zeros(512, dtype=np.uint8),
        center_freq_hz=0,
        sample_rate_hz=0,
        timestamp=0,
    )

    with patch.object(monitor_dialog.chart_widget, "update_data") as mock_update:
        monitor_dialog._on_stream_data(chunk)
        assert not mock_update.called, "Data should not be passed to chart while paused"

    qtbot.mouseClick(monitor_dialog.ui.btnPause, Qt.MouseButton.LeftButton)
    assert monitor_dialog.is_paused is False, "Dialog should exit paused state"
    assert mock_network.request_rf_data_start.called, (
        "Stream should be restarted after unpausing"
    )


def test_data_forwarding(monitor_dialog: ChartMonitorDialog, qtbot) -> None:
    """Перевіряє пряму передачу даних до віджета графіка."""
    chunk = StreamDataChunk(
        stream_type=SourceType.RF,
        data_magnitude=np.array([10, 20, 30], dtype=np.uint8),
        center_freq_hz=915e6,
        sample_rate_hz=10e6,
        timestamp=123.456,
    )

    with patch.object(monitor_dialog.chart_widget, "update_data") as mock_update:
        monitor_dialog._on_stream_data(chunk)
        mock_update.assert_called_once_with(chunk)


def test_close_stops_stream(
    monitor_dialog: ChartMonitorDialog, mock_network: MagicMock
) -> None:
    """Перевіряє коректне завершення потоків при закритті вікна."""
    mock_network.reset_mock()
    monitor_dialog.close()

    assert mock_network.request_rf_data_end.called, (
        "Stream stop request should have been called on close"
    )


def test_chart_mode_change(monitor_dialog: ChartMonitorDialog) -> None:
    """Перевіряє зміну режиму відображення графіка."""
    with patch.object(monitor_dialog.chart_widget, "set_view_mode") as mock_mode:
        monitor_dialog._handle_chart_mode_change("Spectrum Only")
        mock_mode.assert_called_with("Spectrum")

        monitor_dialog._handle_chart_mode_change("Waterfall Only")
        mock_mode.assert_called_with("Waterfall")

        monitor_dialog._handle_chart_mode_change("Both")
        mock_mode.assert_called_with("Both")

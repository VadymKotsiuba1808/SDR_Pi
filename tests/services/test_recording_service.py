"""
Тести для сервісу запису екрану (RecordingService).
"""

from unittest.mock import MagicMock

import pytest

from app.services.recording_service import RecordingService


@pytest.fixture
def mock_system_windows() -> MagicMock:
    """Мок системи для Windows."""
    system = MagicMock()
    system.is_windows = True
    system.is_linux = False
    return system


@pytest.fixture
def mock_system_linux() -> MagicMock:
    """Мок системи для Linux (Raspberry Pi)."""
    system = MagicMock()
    system.is_windows = False
    system.is_linux = True
    return system


def test_setup_variables_windows(mock_system_windows: MagicMock) -> None:
    """Перевірка дефолтних параметрів для Windows."""
    service = RecordingService(mock_system_windows)
    assert service.fps == 30, "Expected FPS 30 for Windows"
    assert service.monitor_index == 1
    assert service.scale_factor == 1.0


def test_setup_variables_linux(mock_system_linux: MagicMock) -> None:
    """Перевірка оптимізованих параметрів для Raspberry Pi."""
    service = RecordingService(mock_system_linux)
    assert service.fps == 10, "Expected FPS 10 for Raspberry Pi"
    assert service.monitor_index == 0
    assert service.scale_factor == 0.5


def test_ffmpeg_params_windows(mock_system_windows: MagicMock) -> None:
    """Параметри FFmpeg для Windows (libx264)."""
    service = RecordingService(mock_system_windows)
    params = service._get_ffmpeg_params(1920, 1080)

    assert params["-vcodec"] == "libx264"
    assert params["-s"] == "1920x1080"
    assert params["-r"] == "30"


def test_ffmpeg_params_linux_sw(mock_system_linux: MagicMock) -> None:
    """Параметри FFmpeg для Linux (програмне кодування)."""
    service = RecordingService(mock_system_linux)
    params = service._get_ffmpeg_params(800, 600, use_hardware=False)

    assert params["-vcodec"] == "libx264"
    assert params["-preset"] == "ultrafast"
    assert params["-r"] == "10"


def test_ffmpeg_params_linux_hw(mock_system_linux: MagicMock) -> None:
    """Параметри FFmpeg для Linux (апаратне кодування h264_v4l2m2m)."""
    service = RecordingService(mock_system_linux)
    params = service._get_ffmpeg_params(800, 600, use_hardware=True)

    assert params["-vcodec"] == "h264_v4l2m2m"
    assert params["-b:v"] == "1000k"


def test_update_duration_logic(mock_system_windows: MagicMock, qtbot) -> None:
    """Логіка підрахунку та форматування тривалості запису."""
    service = RecordingService(mock_system_windows)

    # Імітуємо роботу QElapsedTimer (пройшло 5 секунд)
    service.start_time = MagicMock()
    service.start_time.elapsed.return_value = 5000
    service.prev_total_ms = 0
    service.dif_time_ms = 0

    with qtbot.waitSignal(service.duration_updated, timeout=1000) as blocker:
        service.update_duration()

    assert blocker.args[0] == "00:00:05", "Duration string should be 00:00:05"
    assert service.prev_total_ms == 5000


def test_toggle_pause(mock_system_windows: MagicMock) -> None:
    """Логіка перемикання режиму паузи та накопичення різниці часу."""
    service = RecordingService(mock_system_windows)
    service.start_time = MagicMock()
    service.start_time.elapsed.return_value = 1000

    service.toggle_pause(True)
    assert service.is_paused is True
    assert service.pause_start == 1000

    # Імітуємо перебування на паузі протягом 2 секунд
    service.start_time.elapsed.return_value = 3000
    service.toggle_pause(False)

    assert service.is_paused is False
    assert service.dif_time_ms == 2000

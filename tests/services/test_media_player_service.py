"""
Тести для сервісу медіа-плеєра (MediaPlayerService).
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QProcess

from app.services.media_player_service import MediaPlayerService


@pytest.fixture
def mock_system_service():
    """Фікстура для мока SystemService."""
    service = MagicMock()
    service.is_linux = False
    service.is_windows = True
    return service


@pytest.fixture
def media_player(mock_system_service, qtbot):
    """Фікстура для MediaPlayerService."""
    player = MediaPlayerService(system=mock_system_service)
    return player


def test_vlc_not_found_emits_error(media_player, qtbot):
    """Тест: якщо VLC не знайдено, надсилається сигнал помилки."""
    media_player._vlc_path = None

    with qtbot.wait_signal(media_player.error_occurred) as blocker:
        media_player.play("some_file.mp4")

    assert "VLC" in blocker.args[0]


def test_file_not_found_emits_error(media_player, qtbot):
    """Тест: якщо файл не існує, надсилається сигнал помилки."""
    # Припускаємо, що VLC знайдено
    media_player._vlc_path = "/usr/bin/vlc"

    with patch("os.path.exists", return_value=False):
        with qtbot.wait_signal(media_player.error_occurred) as blocker:
            media_player.play("non_existent.mp4")

    assert "Файл не знайдено" in blocker.args[0]


def test_play_starts_process(media_player, qtbot):
    """Тест успішного запуску процесу VLC."""
    media_player._vlc_path = "vlc"
    file_path = "test_video.mp4"

    # Мокаємо os.path.exists для файлу та QProcess
    with (
        patch("os.path.exists", return_value=True),
        patch("PyQt6.QtCore.QProcess.start") as mock_start,
    ):
        media_player.play(file_path)

        # Перевіряємо, що QProcess.start було викликано
        assert mock_start.called
        args = mock_start.call_args[0][1]
        assert "--fullscreen" in args


def test_stop_closes_process(media_player):
    """Тест зупинки процесу."""
    mock_process = MagicMock(spec=QProcess)
    mock_process.state.return_value = QProcess.ProcessState.Running
    media_player._process = mock_process

    media_player.stop()

    assert mock_process.close.called
    assert media_player._process is None


def test_vlc_executable_searching_windows(mock_system_service):
    """Тест пошуку VLC на Windows."""
    mock_system_service.is_windows = True
    mock_system_service.is_linux = False

    with (
        patch("os.path.exists", side_effect=lambda p: "Program Files" in p),
        patch("shutil.which", return_value=None),
    ):
        player = MediaPlayerService(system=mock_system_service)
        assert player._vlc_path is not None
        assert "vlc.exe" in player._vlc_path


def test_vlc_executable_searching_linux(mock_system_service):
    """Тест пошуку VLC на Linux."""
    mock_system_service.is_windows = False
    mock_system_service.is_linux = True

    with patch("shutil.which", return_value="/usr/bin/vlc"):
        player = MediaPlayerService(system=mock_system_service)
        assert player._vlc_path == "/usr/bin/vlc"

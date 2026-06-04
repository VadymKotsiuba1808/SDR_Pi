"""Тести для сервісу медіа-плеєра."""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QProcess

from app.services.media_player_service import MediaPlayerService


@pytest.fixture
def mock_system_service():
    """Створює мок-об'єкт для SystemService."""
    service = MagicMock()
    service.is_linux = False
    service.is_windows = True
    return service


@pytest.fixture
def media_player(mock_system_service, qtbot):
    """Створює екземпляр MediaPlayerService для тестування."""
    player = MediaPlayerService(system=mock_system_service)
    return player


def test_vlc_not_found_emits_error(media_player, qtbot):
    """Перевіряє генерацію помилки, якщо VLC не знайдено в системі."""
    media_player._vlc_path = None

    with qtbot.wait_signal(media_player.error_occurred) as blocker:
        media_player.play("some_file.mp4")

    assert "VLC" in blocker.args[0], "Error message should mention VLC"


def test_file_not_found_emits_error(media_player, qtbot):
    """Перевіряє генерацію помилки, якщо медіа-файл не існує."""
    media_player._vlc_path = "/usr/bin/vlc"

    with patch("os.path.exists", return_value=False):
        with qtbot.wait_signal(media_player.error_occurred) as blocker:
            media_player.play("non_existent.mp4")

    assert "Файл не знайдено" in blocker.args[0], (
        "Expected 'File not found' error message"
    )


def test_play_starts_process(media_player, qtbot):
    """Перевіряє успішний запуск процесу VLC при відтворенні."""
    media_player._vlc_path = "vlc"
    file_path = "test_video.mp4"

    with (
        patch("os.path.exists", return_value=True),
        patch("PyQt6.QtCore.QProcess.start") as mock_start,
    ):
        media_player.play(file_path)

        assert mock_start.called, "QProcess.start should be called"
        args = mock_start.call_args[0][1]
        assert "--fullscreen" in args, "VLC should be started in fullscreen mode"


def test_stop_closes_process(media_player):
    """Перевіряє коректну зупинку та закриття процесу VLC."""
    mock_process = MagicMock(spec=QProcess)
    mock_process.state.return_value = QProcess.ProcessState.Running
    media_player._process = mock_process

    media_player.stop()

    assert mock_process.close.called, "Process should be closed via .close()"
    assert media_player._process is None, "Process reference should be cleared"


def test_vlc_executable_searching_windows(mock_system_service):
    """Перевіряє логіку пошуку VLC у середовищі Windows."""
    mock_system_service.is_windows = True
    mock_system_service.is_linux = False

    # Симулюємо наявність VLC у папці Program Files
    with (
        patch("os.path.exists", side_effect=lambda p: "Program Files" in p),
        patch("shutil.which", return_value=None),
    ):
        player = MediaPlayerService(system=mock_system_service)
        assert player._vlc_path is not None, "VLC path should be found on Windows"
        assert "vlc.exe" in player._vlc_path, "Executable should be vlc.exe"


def test_vlc_executable_searching_linux(mock_system_service):
    """Перевіряє логіку пошуку VLC у середовищі Linux через PATH."""
    mock_system_service.is_windows = False
    mock_system_service.is_linux = True

    with patch("shutil.which", return_value="/usr/bin/vlc"):
        player = MediaPlayerService(system=mock_system_service)
        assert player._vlc_path == "/usr/bin/vlc", (
            "Should use path from shutil.which on Linux"
        )

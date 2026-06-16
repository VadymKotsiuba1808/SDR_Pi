"""Тестування системних утиліт."""

import sys
from unittest.mock import patch

from app.utils.system_utils import restart_process


def test_restart_process() -> None:
    """Тест перезапуску поточного процесу."""
    # Arrange
    with (
        patch("PyQt6.QtCore.QProcess.startDetached") as mock_start,
        patch("PyQt6.QtCore.QTimer.singleShot") as mock_timer,
    ):
        # Act
        restart_process()

        # Assert
        mock_start.assert_called_once_with(sys.executable, sys.argv)

        # Затримка 8с потрібна, щоб нова копія встигла ініціалізуватися
        assert mock_timer.called, "Expected exit timer to be started"
        assert mock_timer.call_args[0][0] == 8000, (
            f"Expected 8000ms delay, got {mock_timer.call_args[0][0]}"
        )

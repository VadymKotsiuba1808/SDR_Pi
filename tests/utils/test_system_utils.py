"""
Тести для системних утиліт (system_utils).
"""

import sys
from unittest.mock import patch

from app.utils.system_utils import restart_process


def test_restart_process():
    """Тест перезапуску процесу."""
    with (
        patch("PyQt6.QtCore.QProcess.startDetached") as mock_start,
        patch("PyQt6.QtCore.QTimer.singleShot") as mock_timer,
    ):
        restart_process()

        # Перевіряємо, що QProcess.startDetached викликано з поточним виконуваним файлом
        mock_start.assert_called_once_with(sys.executable, sys.argv)

        # Перевіряємо, що таймер на вихід встановлено
        assert mock_timer.called
        assert mock_timer.call_args[0][0] == 8000  # 8 секунд

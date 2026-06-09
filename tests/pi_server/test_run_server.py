"""
Тести для основного скрипта запуску сервера (run_server).
"""

from unittest.mock import MagicMock, patch

from pi_server.run_server import main, signal_handler


def test_signal_handler():
    """Тест обробника сигналів (SIGINT)."""
    with patch("PyQt6.QtCore.QCoreApplication.quit") as mock_quit:
        signal_handler(None, None)
        assert mock_quit.called, "QCoreApplication.quit should be called on signal"


def test_main_initialization():
    """Тест ініціалізації в main()."""
    mock_app = MagicMock()
    mock_server = MagicMock()

    # Мокаємо QCoreApplication, PiServerService та sys.exit
    with (
        patch("pi_server.run_server.QCoreApplication", return_value=mock_app),
        patch("pi_server.run_server.PiServerService", return_value=mock_server),
        patch("pi_server.run_server.signal.signal"),
        patch("sys.exit") as mock_exit,
    ):
        main()

        # Перевіряємо запуск сервера
        assert mock_server.start.called, "Server should be started in main()"

        # Перевіряємо, що exec() було викликано
        assert mock_app.exec.called or mock_app.exec_.called, (
            "app.exec() should be called"
        )

        # Перевіряємо, що sys.exit отримав результат exec
        assert mock_exit.called

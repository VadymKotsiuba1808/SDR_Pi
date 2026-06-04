"""
Тести для основного скрипта запуску сервера (run_server).
"""

from unittest.mock import MagicMock, patch

from pi_server.run_server import main, signal_handler


def test_signal_handler() -> None:
    """Тест обробника сигналів (SIGINT)."""
    # Arrange
    with patch("PyQt6.QtCore.QCoreApplication.quit") as mock_quit:
        # Act
        signal_handler(None, None)

        # Assert
        assert mock_quit.called, "QCoreApplication.quit should be called on signal"


def test_main_initialization() -> None:
    """Тест ініціалізації в main()."""
    # Arrange
    mock_app = MagicMock()
    mock_server = MagicMock()

    with (
        patch("pi_server.run_server.QCoreApplication", return_value=mock_app),
        patch("pi_server.run_server.PiServerService", return_value=mock_server),
        patch("pi_server.run_server.signal.signal"),
        patch("sys.exit") as mock_exit,
    ):
        # Act
        main()

        # Assert
        assert mock_server.start.called, "Server should be started in main()"
        assert mock_app.exec.called or mock_app.exec_.called, (
            "app.exec() should be called"
        )
        assert mock_exit.called, "sys.exit should be called with app execution result"

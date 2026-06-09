import logging
import signal
import sys

from PyQt6.QtCore import QCoreApplication

from app.core.logging_config import get_logger, setup_logging
from pi_server.pi_server_service import PiServerService

logger = get_logger(__name__)


def signal_handler(sig, frame) -> None:
    """Обробник сигналів для коректного завершення роботи програми."""
    logger.info("Stopping server...")
    QCoreApplication.quit()


def main() -> None:
    """Ініціалізація та запуск сервера."""
    app = QCoreApplication(sys.argv)

    signal.signal(signal.SIGINT, signal_handler)

    port = 6000
    server_service = PiServerService(port=port)

    logger.info("Initializing DatabaseService and TCP server...")
    server_service.start()

    logger.info(f"Server started on port {port}. Waiting for clients...")

    sys.exit(app.exec())


if __name__ == "__main__":
    setup_logging(level=logging.DEBUG)
    main()

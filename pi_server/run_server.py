import signal
import sys

from PyQt6.QtCore import QCoreApplication

from app.core.logging_config import get_logger
from pi_server.pi_server_service import PiServerService

logger = get_logger(__name__)


def signal_handler(sig, frame) -> None:
    """Обробник сигналів для коректного завершення роботи програми."""
    logger.info("Зупинка сервера...")
    QCoreApplication.quit()


def main() -> None:
    """Ініціалізація та запуск сервера."""
    app = QCoreApplication(sys.argv)

    signal.signal(signal.SIGINT, signal_handler)

    port = 6000
    server_service = PiServerService(port=port)

    logger.info("Ініціалізація DatabaseService та TCP сервера...")
    server_service.start()

    logger.info(f"Сервер запущено на порту {port}. Очікування клієнтів...")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

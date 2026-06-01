import signal
import sys

from PyQt6.QtCore import QCoreApplication

from pi_server.pi_server_service import PiServerService


def signal_handler(sig, frame) -> None:
    """
    Обробник сигналів для коректного завершення роботи програми.

    Args:
        sig: Номер сигналу (наприклад, SIGINT).
        frame: Поточний кадр стека виконання.
    """
    print("\n[ServerRunner] Зупинка сервера...")
    QCoreApplication.quit()


def main() -> None:
    """
    Головна функція для ініціалізації та запуску сервера.

    Створює екземпляр QCoreApplication, налаштовує обробку переривань
    та запускає PiServerService на порту 6000.
    """
    app = QCoreApplication(sys.argv)

    # Налаштування обробки Ctrl+C (SIGINT) для виходу з циклу подій Qt
    signal.signal(signal.SIGINT, signal_handler)

    # Параметри сервера
    port = 6000
    server_service = PiServerService(port=port)

    print("[ServerRunner] Ініціалізація DatabaseService та TCP сервера...")
    server_service.start()

    print(f"[ServerRunner] Сервер запущено на порту {port}. Очікування клієнтів...")

    # Вхід у цикл подій Qt (Event Loop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

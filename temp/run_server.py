import signal
import sys

from PyQt6.QtCore import QCoreApplication

from temp.pi_server_service import PiServerService


def signal_handler(sig, frame):
    print("\n[ServerRunner] Зупинка сервера...")
    QCoreApplication.quit()


def main():
    app = QCoreApplication(sys.argv)

    # Обробка Ctrl+C для коректного виходу
    signal.signal(signal.SIGINT, signal_handler)

    # Запуск сервера на порту 6000
    port = 6000
    server_service = PiServerService(port=port)

    print("[ServerRunner] Ініціалізація DatabaseService та TCP сервера...")
    server_service.start()

    print("[ServerRunner] Сервер запущено. Очікування клієнтів...")

    # Запускаємо Event Loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

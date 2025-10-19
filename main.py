import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication
import qasync
from app.main_window import MainWindow
from app.services.settings_service import SettingsService


async def main():
    # 1. Створюємо тимчасовий додаток для визначення розміру екрана.
    temp_app = QGuiApplication(sys.argv)
    screen = temp_app.primaryScreen()

    if screen:
        screen_width = screen.geometry().width()

        # 2. Розраховуємо коефіцієнт масштабування.
        base_width = 1920.0
        if screen_width < base_width:
            scale_factor = screen_width / base_width
            os.environ["QT_SCALE_FACTOR"] = str(scale_factor)

    # 3. Видаляємо тимчасовий додаток.
    del temp_app

    # 4. Створюємо основний екземпляр додатку.
    app = QApplication(sys.argv)

    # 5. Ініціалізуємо сервіси.
    settings_service = SettingsService()

    # 6. Створюємо головне вікно.
    window = MainWindow(settings=settings_service)
    window.showFullScreen()

    # 7. Запускаємо Qt event loop інтегрований із asyncio.
    await qasync.qasync.run(app.exec())


if __name__ == '__main__':
    qasync.run(main())

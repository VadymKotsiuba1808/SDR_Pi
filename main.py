import os
import sys
import asyncqt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication
from app.main_window import MainWindow
from app.services.settings_service import SettingsService

if __name__ == '__main__':
    
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

    # Створюємо основний екземпляр додатку.
    app = QApplication(sys.argv)

    # Створюємо спеціальний цикл подій для asyncqt.
    loop = asyncqt.QEventLoop(app)
    
    # Ініціалізуємо сервіс налаштувань.
    settings_service = SettingsService()
    
    # Створюємо головне вікно.
    window = MainWindow(settings=settings_service)
    
    # Показуємо вікно в повноекранному режимі.
    window.showFullScreen()
    
    # Запускаємо головний цикл подій через asyncqt.
    with loop:
        sys.exit(loop.run_forever())
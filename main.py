# -*- coding: utf-8 -*-
import os
import sys
import configparser

# Важливо імпортувати QGuiApplication окремо для визначення екрана
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication

# Імпортуємо наш клас головного вікна
from app.main_window import MainWindow

if __name__ == '__main__':
    
    # --- ✅ КОД ДЛЯ АВТОМАТИЧНОГО МАСШТАБУВАННЯ ---
    
    # 1. Створюємо тимчасовий додаток, щоб отримати доступ до інформації про екран.
    # Це потрібно зробити до створення основного QApplication.
    temp_app = QGuiApplication(sys.argv)
    screen = temp_app.primaryScreen()
    
    if screen: # Перевіряємо, чи екран успішно знайдено
        screen_width = screen.geometry().width()
        
        # 2. Розраховуємо коефіцієнт масштабування відносно базової ширини 1920px.
        base_width = 1920.0
        if screen_width < base_width:
            scale_factor = screen_width / base_width
            # Встановлюємо змінну середовища, яка змусить Qt масштабувати інтерфейс.
            os.environ["QT_SCALE_FACTOR"] = str(scale_factor)
            
    # 3. Видаляємо тимчасовий додаток, він більше не потрібен.
    del temp_app
    # --------------------------------------------------------

    # Створюємо основний екземпляр додатку, який вже врахує QT_SCALE_FACTOR.
    app = QApplication(sys.argv)
    
    # Читаємо конфігураційний файл
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    if not config.sections():
        print("ПОМИЛКА: Не вдалося завантажити config.ini. Переконайтеся, що файл існує.")
        sys.exit(1)
        
    # Створюємо головне вікно
    window = MainWindow(settings=config)
    
    # Показуємо вікно (рекомендується використовувати showMaximized для кращого вигляду)
    #window.showMaximized()
    window.showFullScreen()
    
    # Запускаємо головний цикл
    sys.exit(app.exec())
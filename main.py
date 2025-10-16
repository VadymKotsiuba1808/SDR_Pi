# -*- coding: utf-8 -*-
import sys
import configparser
from PyQt5.QtWidgets import QApplication

# Імпортуємо наш клас головного вікна
from app.main_window import MainWindow

if __name__ == '__main__':
    # 1. Створюємо екземпляр додатку
    app = QApplication(sys.argv)
    
    # 2. Читаємо конфігураційний файл
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    # Перевірка, чи файл конфігурації завантажився
    if not config.sections():
        print("ПОМИЛКА: Не вдалося завантажити config.ini. Переконайтеся, що файл існує.")
        sys.exit(1)
        
    # 3. Створюємо головне вікно, передаючи йому об'єкт конфігурації
    window = MainWindow(settings=config)
    
    # 4. Показуємо вікно
    window.show()
    
    # 5. Запускаємо головний цикл
    sys.exit(app.exec_())


import os

from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QFileSystemWatcher

class SettingsService(QObject):
    """
    Централізований сервіс для керування налаштуваннями додатку.
    Використовує явні атрибути для надійності та зручності.
    """
    # Сигнал, який сповіщає всю програму про те, що налаштування оновилися
    settings_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        file_path=os.path.join(os.path.dirname(__file__), "../../config.ini")
        file_path = os.path.abspath(file_path)
        # --- Ініціалізація QSettings ---
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        self.settings_file = QSettings(file_path, QSettings.Format.IniFormat)
        print(self.settings_file)

        # --- Явні атрибути з налаштуваннями (значення за замовчуванням) ---
        self.host='0.0.0.0'
        self.port=5000
        self.radar_radius = 500
        self.radar_max_radius=1000
        self.api_key=''
        self.base_url='https://maps.googleapis.com/maps/api/staticmap?'
        self.scale=2
        
        # Додавайте сюди інші налаштування за потреби

        # --- Запуск відстеження файлу ---
        self.watcher = QFileSystemWatcher([self.settings_file.fileName()])
        self.watcher.fileChanged.connect(self._reload_from_file)

        # Завантажуємо налаштування при першому запуску
        self._reload_from_file()

    def _reload_from_file(self):
        """
        ПРИВАТНИЙ МЕТОД: Перезавантажує всі налаштування з файлу.
        Використовується при старті та при зовнішній зміні config.ini.
        """
        print("Перезавантаження налаштувань з config.ini...")
        
        # Примусово читаємо файл з диска
        self.settings_file.sync() 

        # Оновлюємо поля класу новими значеннями з файлу
        self.host= self.settings_file.value("network/host", self.host)
        self.port= self.settings_file.value("network/port", self.port)
        self.radar_radius = self.settings_file.value("maps/radar_radius", self.radar_radius, type=int)
        self.radar_max_radius=self.settings_file.value("maps/radar_max_radius", self.radar_max_radius, type=int)
        self.api_key=self.settings_file.value("maps/api_key", self.api_key)
        self.base_url=self.settings_file.value("maps/base_url", self.base_url)
        self.scale=self.settings_file.value("maps/scale", self.scale)

        # Сповіщаємо всі частини програми, що налаштування змінилися
        self.settings_changed.emit()

    def update_setting(self, key: str, value):
        """
        ПУБЛІЧНИЙ МЕТОД: Оновлює одне налаштування.
        Записує його у файл та оновлює поле в класі.
        """
        print(f"Оновлення налаштування '{key}' на значення '{value}'")

        # 1. Перевіряємо, чи такий ключ налаштування взагалі існує
        if not self.settings_file.contains(key):
             # Можна також перевіряти по явних атрибутах, але contains надійніше
             print(f"Увага: Невідомий ключ налаштування '{key}'")
             return

        # 2. Записуємо нове значення у файл config.ini
        self.settings_file.setValue(key, value)

        # 3. Оновлюємо відповідне поле в цьому класі
        # Використовуємо setattr для динамічного оновлення атрибута за його назвою
        attribute_name = key.split('/')[-1] # Отримуємо "radar_radius" з "main/radar_radius"
        if hasattr(self, attribute_name):
            # Перетворюємо тип, якщо потрібно
            current_type = type(getattr(self, attribute_name))
            setattr(self, attribute_name, current_type(value))
        
        # 4. Сповіщаємо додаток про зміни
        self.settings_changed.emit()
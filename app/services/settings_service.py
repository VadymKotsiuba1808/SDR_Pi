from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QFileSystemWatcher

class SettingsService(QObject):
    """
    Централізований сервіс для керування налаштуваннями додатку.
    Використовує явні атрибути для надійності та зручності.
    """
    # Сигнал, який сповіщає всю програму про те, що налаштування оновилися
    settings_changed = pyqtSignal()

    def __init__(self, file_path="config.ini"):
        super().__init__()

        # --- Ініціалізація QSettings ---
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        self.settings_file = QSettings(file_path)

        # --- Явні атрибути з налаштуваннями (значення за замовчуванням) ---
        self.window_title = "SDR Drone Detector"
        self.radar_radius = 500
        self.show_radar = True
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
        self.window_title = self.settings_file.value("main/title", self.window_title)
        self.radar_radius = self.settings_file.value("main/radar_radius", self.radar_radius, type=int)
        self.show_radar = self.settings_file.value("main/show_radar", self.show_radar, type=bool)

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
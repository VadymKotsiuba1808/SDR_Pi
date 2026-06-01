import os
import platform
import sys


class SystemService:
    """
    Сервіс для отримання інформації про операційну систему та оточення.

    Цей сервіс надає централізований доступ до параметрів хост-системи,
    що дозволяє адаптувати логіку програми (наприклад, шляхи до файлів,
    команди FFmpeg або взаємодію з ОС) під різні платформи (Windows або Linux).

    Attributes:
        os (str): Назва операційної системи (наприклад, 'Windows', 'Linux').
        python_version (str): Повна версія інтерпретатора Python.
        is_windows (bool): True, якщо програма запущена на Windows.
        is_linux (bool): True, якщо програма запущена на Linux.
        app_dir (str): Абсолютний шлях до директорії, де розташований цей файл.
    """

    def __init__(self) -> None:
        """
        Ініціалізує сервіс та визначає параметри поточної системи.
        """
        self.os: str = platform.system()
        self.python_version: str = sys.version
        self.is_windows: bool = self.os == "Windows"
        self.is_linux: bool = self.os == "Linux"
        # Визначаємо шлях до директорії сервісів для коректного пошуку ресурсів.
        self.app_dir: str = os.path.dirname(os.path.abspath(__file__))

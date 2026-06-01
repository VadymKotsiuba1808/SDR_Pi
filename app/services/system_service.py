import os
import platform
import sys


class SystemService:
    """
    Сервіс надання інформації про операційну систему.

    Використовується для адаптації поведінки програми (шляхи до файлів,
    команди кодування відео, перемикання розкладок) під Windows або Linux.
    """

    def __init__(self):
        """Ініціалізує сервіс та збирає дані про систему."""
        self.os = platform.system()  # "Windows", "Linux", "Darwin"
        self.python_version = sys.version
        self.is_windows = self.os == "Windows"
        self.is_linux = self.os == "Linux"
        self.app_dir = os.path.dirname(os.path.abspath(__file__))

import os
import platform
import sys


class SystemService:
    """Сервіс для отримання інформації про операційну систему та оточення."""

    def __init__(self) -> None:
        self.os: str = platform.system()
        self.python_version: str = sys.version
        self.is_windows: bool = self.os == "Windows"
        self.is_linux: bool = self.os == "Linux"
        self.app_dir: str = os.path.dirname(os.path.abspath(__file__))

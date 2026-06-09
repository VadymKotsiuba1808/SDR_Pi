import os
import platform
import sys


class SystemService:
    def __init__(self):
        self.os = platform.system()  # "Windows", "Linux", "Darwin"
        self.python_version = sys.version
        self.is_windows = self.os == "Windows"
        self.is_linux = self.os == "Linux"
        self.app_dir = os.path.dirname(os.path.abspath(__file__))

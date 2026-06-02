import sys

from PyQt6.QtCore import QCoreApplication, QProcess, QTimer


def restart_process() -> None:
    QProcess.startDetached(sys.executable, sys.argv)
    # Затримка перед виходом для стабільного запуску нової копії
    QTimer.singleShot(8000, QCoreApplication.quit)

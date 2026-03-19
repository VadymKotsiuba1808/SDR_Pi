import sys
from PyQt6.QtCore import QCoreApplication, QProcess, QTimer


def restart_process():
    QProcess.startDetached(sys.executable, sys.argv)
    QTimer.singleShot(8000, QCoreApplication.quit)

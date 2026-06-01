import sys

from PyQt6.QtCore import QCoreApplication, QProcess, QTimer


def restart_process() -> None:
    """
    Перезапускає поточний процес додатка.

    Використовує `QProcess.startDetached` для запуску нової копії додатка з тими ж
    аргументами командного рядка, після чого завершує поточний процес через таймер.

    !!! note
        Використання затримки перед `QCoreApplication.quit` допомагає уникнути
        можливих конфліктів при швидкому перезапуску ресурсів.
    """
    QProcess.startDetached(sys.executable, sys.argv)
    # Затримка перед виходом для стабільного запуску нової копії
    QTimer.singleShot(8000, QCoreApplication.quit)

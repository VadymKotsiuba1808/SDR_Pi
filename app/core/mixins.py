import os

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QWidget


class TranslatorMixin:
    """
    Додає підтримку методу tr() для класів, що не є QObject.
    Автоматично визначає ім'я класу як контекст перекладу.
    """

    def tr(self, text: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, text)

    @classmethod
    def tr_s(cls, text: str) -> str:
        return QCoreApplication.translate(cls.__name__, text)


class TestUIOptimizationMixin:
    """
    Міксин для оптимізації відображення вікон під час автоматизованого тестування.
    Якщо встановлено змінну оточення SDR_PI_TESTING, вікно автоматично згортається.
    """

    def apply_test_ui_optimization(self) -> None:
        if os.environ.get("SDR_PI_TESTING") == "1":
            # Перевіряємо, чи об'єкт має метод setWindowState (тобто є QWidget)
            if isinstance(self, QWidget):
                self.setWindowState(Qt.WindowState.WindowMinimized)

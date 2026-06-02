import os

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QWidget


class TranslatorMixin:
    """
    Міксин для додавання підтримки методу `tr()` у класи, які не успадковуються від QObject.

    Цей клас дозволяє використовувати механізм перекладів Qt у будь-якому класі,
    автоматично використовуючи ім'я класу як контекст для пошуку перекладів.
    """

    def tr(self, text: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, text)

    @classmethod
    def tr_s(cls, text: str) -> str:
        return QCoreApplication.translate(cls.__name__, text)


class TestUIOptimizationMixin:
    """
    Міксин для оптимізації поведінки GUI під час автоматизованого тестування.

    Дозволяє уникнути перекриття екрана вікнами під час виконання тестів,
    що важливо для CI середовищ та паралельного виконання тестів.
    """

    def apply_test_ui_optimization(self) -> None:
        if os.environ.get("SDR_PI_TESTING") == "1":
            # Мінімізація вікна запобігає захопленню фокусу під час тестів.
            if isinstance(self, QWidget):
                self.setWindowState(Qt.WindowState.WindowMinimized)

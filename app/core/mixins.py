from PyQt6.QtCore import QCoreApplication


class TranslatorMixin:
    """
    Додає підтримку методу tr() для класів, що не є QObject.
    Автоматично визначає ім'я класу як контекст перекладу.
    """

    def tr(self, text: str, disambiguation: str = None, n: int = -1) -> str:
        return QCoreApplication.translate(
            self.__class__.__name__, text, disambiguation, n
        )

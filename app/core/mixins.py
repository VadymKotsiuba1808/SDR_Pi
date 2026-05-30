from PyQt6.QtCore import QCoreApplication


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

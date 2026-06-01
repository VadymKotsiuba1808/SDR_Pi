"""
Тести для міксинів (TranslatorMixin).
"""

from unittest.mock import patch

from app.core.mixins import TranslatorMixin


class DummyClass(TranslatorMixin):
    """
    Клас для тестування TranslatorMixin.

    Використовується як мінімальна реалізація для перевірки методів tr та tr_s.
    """

    pass


def test_translator_mixin_tr() -> None:
    """
    Тест методу tr() міксина.

    Перевіряє, що екземпляр класу правильно викликає QCoreApplication.translate
    з власним іменем як контекстом.
    """
    obj = DummyClass()
    with patch(
        "PyQt6.QtCore.QCoreApplication.translate", return_value="translated"
    ) as mock_translate:
        result = obj.tr("hello")

        assert result == "translated", "tr() should return translated text"
        mock_translate.assert_called_once_with("DummyClass", "hello")


def test_translator_mixin_tr_s() -> None:
    """
    Тест класового методу tr_s() міксина.

    Перевіряє, що статичний метод правильно використовує ім'я класу
    як контекст для перекладу без створення екземпляра.
    """
    with patch(
        "PyQt6.QtCore.QCoreApplication.translate", return_value="translated_static"
    ) as mock_translate:
        result = DummyClass.tr_s("world")

        assert result == "translated_static", (
            "tr_s() should return translated text for static call"
        )
        mock_translate.assert_called_once_with("DummyClass", "world")

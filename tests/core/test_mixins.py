"""
Юніт-тести для міксинів, що забезпечують допоміжну функціональність ядра.

Цей модуль містить тести для `TranslatorMixin`, який дозволяє використовувати
стандартний механізм інтернаціоналізації Qt (tr) у класах, що не є
нащадками `QObject`. Це важливо для підтримки перекладів у моделях даних
та сервісах без накладних витрат на повну ієрархію `QObject`.
"""

from unittest.mock import patch

from app.core.mixins import TranslatorMixin


class DummyClass(TranslatorMixin):
    """Мінімальний клас для ізольованого тестування `TranslatorMixin`."""

    pass


def test_translator_mixin_tr() -> None:
    """Перевірка методу екземпляра `tr()` на коректність контексту перекладу."""
    obj = DummyClass()
    with patch(
        "PyQt6.QtCore.QCoreApplication.translate", return_value="translated"
    ) as mock_translate:
        result = obj.tr("hello")

        assert result == "translated", (
            "tr() method should return the translation received from Qt"
        )
        mock_translate.assert_called_once_with("DummyClass", "hello")


def test_translator_mixin_tr_s() -> None:
    """Перевірка статичного методу `tr_s()` для отримання перекладу без створення екземпляра."""
    with patch(
        "PyQt6.QtCore.QCoreApplication.translate", return_value="translated_static"
    ) as mock_translate:
        result = DummyClass.tr_s("world")

        assert result == "translated_static", (
            "tr_s() method should return translation on static call"
        )
        mock_translate.assert_called_once_with("DummyClass", "world")

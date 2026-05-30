"""
Тести для міксинів (TranslatorMixin).
"""

from unittest.mock import patch

from app.core.mixins import TranslatorMixin


class DummyClass(TranslatorMixin):
    """Клас для тестування TranslatorMixin."""

    pass


def test_translator_mixin_tr():
    """Тест методу tr() міксина."""
    obj = DummyClass()
    with patch(
        "PyQt6.QtCore.QCoreApplication.translate", return_value="translated"
    ) as mock_translate:
        result = obj.tr("hello")

        assert result == "translated"
        mock_translate.assert_called_once_with("DummyClass", "hello")


def test_translator_mixin_tr_s():
    """Тест класового методу tr_s() міксина."""
    with patch(
        "PyQt6.QtCore.QCoreApplication.translate", return_value="translated_static"
    ) as mock_translate:
        result = DummyClass.tr_s("world")

        assert result == "translated_static"
        mock_translate.assert_called_once_with("DummyClass", "world")

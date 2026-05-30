"""
Тести для валідатора паролів.
"""

from unittest.mock import patch

import pytest

from app.validators.password_validator import PasswordValidator


@pytest.fixture
def validator():
    """
    Фікстура для ініціалізації PasswordValidator з вимкненим перекладом.
    """
    with patch(
        "app.validators.password_validator.PasswordValidator.tr",
        side_effect=lambda x: x,
    ):
        v = PasswordValidator(min_length=6)
        yield v


def test_password_valid(validator) -> None:
    """
    Тест валідного пароля.
    """
    assert validator.validate("secure123!") is True
    # Перевіряємо, що в усіх ключах списки помилок порожні
    errors = validator.get_errors()
    assert all(not v for v in errors.values())


def test_password_too_short(validator) -> None:
    """
    Тест занадто короткого пароля.
    """
    assert validator.validate("12345") is False
    errors = validator.get_errors()
    assert "password" in errors
    assert any("at least 6 characters" in msg for msg in errors["password"])


def test_password_empty(validator) -> None:
    """
    Тест порожнього пароля.
    """
    assert validator.validate("") is False
    assert "password" in validator.get_errors()


def test_password_invalid_characters(validator) -> None:
    """
    Тест пароля з недозволеними символами.
    """
    # Припустимо, кирилиця не дозволена
    assert validator.validate("пароль123") is False
    assert any(
        "invalid characters" in msg for msg in validator.get_errors()["password"]
    )

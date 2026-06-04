"""Модуль для тестування валідатора паролів."""

from typing import Generator
from unittest.mock import patch

import pytest

from app.validators.password_validator import PasswordValidator


@pytest.fixture
def validator() -> Generator[PasswordValidator, None, None]:
    """Створює екземпляр PasswordValidator з мокованим перекладом."""
    with patch(
        "app.validators.password_validator.PasswordValidator.tr",
        side_effect=lambda x: x,
    ):
        v = PasswordValidator(min_length=6)
        yield v


def test_password_valid(validator: PasswordValidator) -> None:
    """Перевіряє успішну валідацію коректного пароля."""
    assert validator.validate("secure123!") is True, "Valid password should be accepted"
    errors = validator.get_errors()
    assert all(not v for v in errors.values()), (
        "Error list should be empty for a valid password"
    )


def test_password_too_short(validator: PasswordValidator) -> None:
    """Перевіряє відхилення пароля, довжина якого менша за мінімально допустиму."""
    assert validator.validate("12345") is False, (
        "Password shorter than min_length should be rejected"
    )
    errors = validator.get_errors()
    assert "password" in errors, (
        "Error key 'password' should be present in errors dictionary"
    )
    assert any("at least 6 characters" in msg for msg in errors["password"]), (
        "Should contain a message about minimum character length"
    )


def test_password_empty(validator: PasswordValidator) -> None:
    """Перевіряє відхилення порожнього пароля."""
    assert validator.validate("") is False, "Empty password should be rejected"
    assert "password" in validator.get_errors(), (
        "Empty password should trigger a validation error"
    )


def test_password_invalid_characters(validator: PasswordValidator) -> None:
    """Перевіряє відхилення пароля, що містить недозволені символи."""
    assert validator.validate("пароль123") is False, (
        "Password with Cyrillic characters should be rejected"
    )
    assert any(
        "invalid characters" in msg for msg in validator.get_errors()["password"]
    ), "Should contain an 'invalid characters' error message"

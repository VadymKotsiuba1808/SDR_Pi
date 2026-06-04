"""Модуль тестів для утиліт роботи з паролями."""

from app.utils.password_utils import hash_password, verify_password


def test_hash_password() -> None:
    password = "test_password"
    hashed = hash_password(password)
    assert hashed != password, "Hash should not match the plain password"
    assert len(hashed) > 0, "Hash should not be empty"


def test_verify_password_correct() -> None:
    password = "secret_password"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True, (
        "Valid password should be verified"
    )


def test_verify_password_incorrect() -> None:
    password = "correct_password"
    hashed = hash_password(password)
    assert verify_password("wrong_password", hashed) is False, (
        "Invalid password should be rejected"
    )


def test_verify_password_invalid_hash() -> None:
    assert verify_password("password", "invalid_hash") is False, (
        "Invalid hash should return False"
    )

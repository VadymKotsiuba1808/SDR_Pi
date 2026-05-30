"""
Тести для утиліт паролів.
"""

from app.utils.password_utils import hash_password, verify_password


def test_hash_password() -> None:
    """
    Тест хешування пароля.
    """
    password = "test_password"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 0


def test_verify_password_correct() -> None:
    """
    Тест успішної перевірки пароля.
    """
    password = "secret_password"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect() -> None:
    """
    Тест перевірки з неправильним паролем.
    """
    password = "correct_password"
    hashed = hash_password(password)
    assert verify_password("wrong_password", hashed) is False


def test_verify_password_invalid_hash() -> None:
    """
    Тест перевірки з пошкодженим хешем.
    """
    assert verify_password("password", "invalid_hash") is False

from passlib.context import CryptContext

# Контекст для хешування паролів. Використовує bcrypt.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Перевіряє відповідність відкритого пароля його хешу."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Повертаємо False замість винятку, щоб запобігти витоку інформації
        # про структуру хешу та забезпечити стійкість до пошкоджених даних.
        return False

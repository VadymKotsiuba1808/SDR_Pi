from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(plain_password: str) -> str:
    #Вже з сіллю
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Використовуємо try-except, оскільки passlib може 
    # кинути виняток, якщо хеш пошкоджений або має невідомий формат.
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False
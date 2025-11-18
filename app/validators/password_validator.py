import string
from app.validators.base_validator import BaseValidator


class PasswordValidator(BaseValidator):
    """
    Валідує пароль за набором критеріїв.
    """

    def __init__(
        self,
        min_length=4,
    ):
        """
        Ініціалізує валідатор з гнучкими правилами.

        """
        super().__init__()
        self.min_length = min_length

        # Визначаємо набір "безпечних" символів
        self.allowed_characters = set(
            string.ascii_letters + string.digits + string.punctuation
        )

    def validate(self, password):
        self._errors.clear()
        """
        Запускає всі перевірки для наданого пароля.
        """

        self._password_validate(password)

        return self._is_valid()

    def _password_validate(self, password):
        self._errors["password"] = []

        # Базові перевірки (Тип та порожній рядок) ---

        if not password or not isinstance(password, str):
            self._errors["password"].append(
                "Пароль повинен бути рядком і не може бути порожнім."
            )
            # Якщо це не рядок, подальші перевірки не мають сенсу
            return

        # Перевірка чи всі символи є "дозволеними" (букви, цифри, пунктуація)
        if not all(c in self.allowed_characters for c in password):
            self._errors["password"].append("Пароль містить неприпустимі символи.")

        # Перевірка мінімальної довжини ---
        if len(password) < self.min_length:
            self._errors["password"].append(
                f"Пароль повинен мати принаймні {self.min_length} символи."
            )

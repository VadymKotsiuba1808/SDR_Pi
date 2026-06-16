import string
from typing import Set

from app.core.mixins import TranslatorMixin
from app.validators.base_validator import BaseValidator


class PasswordValidator(BaseValidator, TranslatorMixin):
    """
    Валідатор для перевірки складності та коректності пароля.

    Клас реалізує набір правил для забезпечення безпеки паролів користувачів,
    включаючи перевірку довжини та дозволених символів.
    """

    def __init__(
        self,
        min_length: int = 6,
    ) -> None:
        super().__init__()
        self.min_length: int = min_length

        self.allowed_characters: Set[str] = set(
            string.ascii_letters + string.digits + string.punctuation
        )

    def validate(self, data: str) -> bool:
        """Виконує повну валідацію наданого пароля."""
        self._errors.clear()
        self._password_validate(data)

        return self._is_valid()

    def _password_validate(self, password: str) -> None:
        self._errors["password"] = []

        if not password or not isinstance(password, str):
            self._errors["password"].append(
                self.tr("The password must be a string and cannot be empty.")
            )
            return

        if not all(c in self.allowed_characters for c in password):
            self._errors["password"].append(
                self.tr("The password contains invalid characters.")
            )

        if len(password) < self.min_length:
            template = self.tr("Password must be at least {count} characters long.")
            msg = template.format(count=self.min_length)

            self._errors["password"].append(msg)

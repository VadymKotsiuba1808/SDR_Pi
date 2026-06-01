"""
Базовий валідатор.
Абстрактний клас, що визначає єдиний інтерфейс та методи (наприклад, `validate` та `get_errors`) для всіх механізмів перевірки вхідних даних у програмі.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseValidator(ABC):
    """
    Абстрактний базовий клас (шаблон) для всіх валідаторів.
    """

    def __init__(self):
        self._errors = {}

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """Головний метод, який запускає всі перевірки."""
        self._errors.clear()
        return self._is_valid()

    def _is_valid(self):
        """Перевіряє, чи були помилки."""
        for value in self._errors.values():
            if len(value) > 0:
                return False

        return True

    def get_errors(self):
        """Повертає словник з усіма помилками валідації."""
        return self._errors

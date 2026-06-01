from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseValidator(ABC):
    """
    Абстрактний базовий клас для всіх валідаторів у системі.

    Забезпечує спільний механізм для зберігання помилок та перевірки стану валідації.
    """

    def __init__(self) -> None:
        self._errors: Dict[str, List[str]] = {}

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """Головний метод, який запускає всі перевірки."""
        self._errors.clear()
        return self._is_valid()

    def _is_valid(self) -> bool:
        for value in self._errors.values():
            if len(value) > 0:
                return False

        return True

    def get_errors(self) -> Dict[str, List[str]]:
        return self._errors

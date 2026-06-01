from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseValidator(ABC):
    """
    Абстрактний базовий клас для всіх валідаторів у системі.

    Забезпечує спільний механізм для зберігання помилок та перевірки стану валідації.
    """

    def __init__(self) -> None:
        """
        Ініціалізує валідатор з порожнім словником помилок.
        """
        self._errors: Dict[str, List[str]] = {}

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """
        Головний метод, який запускає процес валідації.

        Очищує попередні помилки перед початком нової перевірки.

        Args:
            data: Дані, які необхідно перевірити.

        Returns:
            bool: True, якщо дані пройшли валідацію, інакше False.
        """
        self._errors.clear()
        return self._is_valid()

    def _is_valid(self) -> bool:
        """
        Перевіряє внутрішній стан на наявність помилок.

        Returns:
            bool: True, якщо жодної помилки не було знайдено, інакше False.
        """
        for value in self._errors.values():
            if len(value) > 0:
                return False

        return True

    def get_errors(self) -> Dict[str, List[str]]:
        """
        Повертає словник зі списком помилок для кожного поля.

        Returns:
            Dict[str, List[str]]: Словник, де ключі — це назви полів, а значення — списки повідомлень про помилки.
        """
        return self._errors

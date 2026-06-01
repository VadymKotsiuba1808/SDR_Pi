import asyncio
from typing import Any, Callable


def make_safe_set_result(future: asyncio.Future[Any]) -> Callable[[Any], None]:
    """
    Створює безпечну функцію-обробник (слот) для встановлення результату в Future.

    Ця утиліта корисна при інтеграції сигналів Qt з асинхронним кодом. Вона гарантує,
    що спроба встановити результат не призведе до помилки `InvalidStateError`, якщо Future
    вже було завершено (наприклад, через таймаут або скасування).

    Args:
        future: Об'єкт `asyncio.Future`, результат якого потрібно встановити.

    Returns:
        Обгортка (слот), яка приймає результат сигналу та безпечно оновлює Future.
    """

    def safe_set_result(result_code: Any) -> None:
        if not future.done():
            future.set_result(result_code)

    return safe_set_result

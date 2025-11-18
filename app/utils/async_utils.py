import asyncio
from typing import Callable


def make_safe_set_result(future: asyncio.Future) -> Callable:
    """
    Повертає слот для Qt сигналу, який встановлює результат у Future
    тільки якщо він ще не завершений.
    """

    def safe_set_result(result_code):
        if not future.done():
            future.set_result(result_code)

    return safe_set_result

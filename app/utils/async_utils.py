import asyncio
from typing import Any, Callable


def make_safe_set_result(future: asyncio.Future[Any]) -> Callable[[Any], None]:
    """Створює безпечну функцію для встановлення результату в Future (запобігає InvalidStateError)."""

    def safe_set_result(result_code: Any) -> None:
        if not future.done():
            future.set_result(result_code)

    return safe_set_result

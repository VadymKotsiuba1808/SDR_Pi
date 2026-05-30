"""
Тести для асинхронних утиліт (async_utils).
"""

import asyncio

import pytest

from app.utils.async_utils import make_safe_set_result


@pytest.mark.anyio
async def test_make_safe_set_result():
    """Тест безпечного встановлення результату у Future."""
    future = asyncio.Future()
    safe_setter = make_safe_set_result(future)

    # Перше встановлення - успішне
    safe_setter(10)
    assert future.result() == 10

    # Друге встановлення - не повинно викликати винятку InvalidStateError
    safe_setter(20)
    assert future.result() == 10

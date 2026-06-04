"""Тести для асинхронних утиліт."""

import asyncio

import pytest

from app.utils.async_utils import make_safe_set_result


@pytest.mark.anyio
async def test_make_safe_set_result() -> None:
    future: asyncio.Future[int] = asyncio.Future()
    safe_setter = make_safe_set_result(future)

    safe_setter(10)
    assert future.result() == 10, f"Expected result 10, got {future.result()}"

    safe_setter(20)
    assert future.result() == 10, (
        "Future result should not change after the second safe_setter call"
    )

import pytest
import asyncio
import re

from pytest_mock import MockerFixture
from unittest.mock import Mock, AsyncMock

from nano_dev_utils.timers import Timer
from .conftest import assert_called_w_substr


@pytest.mark.asyncio
async def test_async_function_timing(
    timer_mock: Timer, async_sleep_mocker: AsyncMock
) -> None:
    """Test timing of simple async functions."""

    @timer_mock.timeit()
    async def async_noop():
        return 'done'

    result = await async_noop()
    assert result == 'done'


@pytest.mark.asyncio
async def test_timer_async_function(
    timer_mock: Timer,
    mock_logger: Mock,
    mock_print: Mock,
    mocker: MockerFixture,
    async_sleep_mocker: AsyncMock,
) -> None:
    mocker.patch('asyncio.sleep', async_sleep_mocker)

    pattern = r'fast_async took\s+([0-9]*\.[0-9]+)\s*\[?(ns|μs)]?'

    timer_mock.init(precision=6)

    timer_mock.update({'printout': True})

    expected_func_name = 'fast_async'

    @timer_mock.timeit()
    async def fast_async(x):
        await asyncio.sleep(0.05)
        return x * 2

    result = await fast_async(10)
    assert result == 20

    log_args_list = assert_called_w_substr(mock_logger.info, expected_func_name)
    assert_called_w_substr(mock_print, expected_func_name)

    for log_args in log_args_list:
        assert re.search(pattern, log_args)


@pytest.mark.asyncio
async def test_async_function_with_args(
    timer_mock: Timer, async_sleep_mocker: AsyncMock
) -> None:
    """Test async function with arguments."""

    @timer_mock.timeit()
    async def async_add(a: int, b: int):
        return a + b

    result = await async_add(5, 3)
    assert result == 8


@pytest.mark.asyncio
async def test_async_function_with_delay(
    timer_mock: Timer, async_sleep_mocker: AsyncMock
) -> None:
    """Test async function that would normally have delay."""

    @timer_mock.timeit()
    async def async_with_sleep():
        await asyncio.sleep(1)
        return 'completed'

    result = await async_with_sleep()
    assert result == 'completed'

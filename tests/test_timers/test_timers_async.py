import pytest
import asyncio
import re

from pytest_mock import MockerFixture
from unittest.mock import Mock, AsyncMock

from nano_dev_utils import timer
from nano_dev_utils.timers import Timer


@pytest.fixture
def async_sleep_mocker(mocker: MockerFixture) -> AsyncMock:
    """Mock asyncio.sleep to speed up tests."""

    async def noop_sleep(t):
        pass

    return mocker.patch('asyncio.sleep', side_effect=noop_sleep)


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
    mock_logger: Mock, mocker: MockerFixture, async_sleep_mocker: AsyncMock
) -> None:
    mocker.patch('asyncio.sleep', async_sleep_mocker)
    timer.init(precision=6)

    @timer.timeit()
    async def fast_async(x):
        await asyncio.sleep(0.05)
        return x * 2

    result = await fast_async(10)
    assert result == 20
    assert mock_logger.info.called
    log_args = mock_logger.info.call_args[0][0]
    assert 'fast_async' in log_args
    assert re.search(r'fast_async took\s+([0-9]*\.[0-9]+)\s*\[?(ns|μs)]?', log_args)


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

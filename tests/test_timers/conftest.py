import pytest
import logging

from pytest_mock import MockerFixture
from unittest.mock import Mock, AsyncMock
from typing import Callable

from nano_dev_utils import timers, timer
from nano_dev_utils.timers import Timer


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> Mock:
    mock_logger = mocker.MagicMock(spec=logging.Logger)
    timers.lgr = mock_logger
    return mock_logger


@pytest.fixture
def timer_mock() -> Timer:
    return timer


@pytest.fixture
def res_form_mock() -> Callable[..., str]:
    return timer.res_formatter


@pytest.fixture
def async_sleep_mocker(mocker: MockerFixture) -> AsyncMock:
    """Mock asyncio.sleep to speed up tests."""

    async def noop_sleep(t):
        pass

    return mocker.patch('asyncio.sleep', side_effect=noop_sleep)

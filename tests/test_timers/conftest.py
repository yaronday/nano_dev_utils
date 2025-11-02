import pytest
import logging
import builtins

from pytest_mock import MockerFixture
from unittest.mock import patch, Mock, AsyncMock
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


@pytest.fixture
def mock_print() -> Mock:
    with patch.object(builtins, 'print') as mock_print_fn:
        yield mock_print_fn


def assert_called_with_substr(mock_obj: Mock, substring: str) -> str:
    assert mock_obj.called
    arg_str = mock_obj.call_args[0][0]
    assert substring in arg_str
    return arg_str


import pytest
import logging
import builtins

from pytest_mock import MockerFixture
from unittest.mock import patch, Mock, AsyncMock
from typing import Callable, Generator

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
def mock_print() -> Generator[Mock, None, None]:
    with patch.object(builtins, 'print') as mock_print_fn:
        yield mock_print_fn


def assert_called_w_substr(mock_obj: Mock, substr: str) -> list[str]:
    assert mock_obj.called, 'Mock object was not called'

    all_calls = mock_obj.call_args_list
    call_args_strs: list[str] = []

    for call in all_calls:
        first_arg = call[0][0]
        assert isinstance(first_arg, str), (
            f'Expected str argument, got {type(first_arg)}'
        )
        assert substr in first_arg, (
            f"Substring '{substr}' not found in call argument '{first_arg}'"
        )
        call_args_strs.append(first_arg)

    return call_args_strs

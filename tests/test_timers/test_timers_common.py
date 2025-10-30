import pytest
import logging

from pytest_mock import MockerFixture
from unittest.mock import Mock
from nano_dev_utils import timers, timer
from nano_dev_utils.timers import Timer

SIM_COMPLETE_TIME = 'Function completed in simulated'


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> Mock:
    mock_logger = mocker.MagicMock(spec=logging.Logger)
    timers.lgr = mock_logger
    return mock_logger


@pytest.fixture
def timer_mock() -> Timer:
    return timer

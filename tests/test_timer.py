import threading
import asyncio
import pytest
import logging
import re

from pytest_mock import MockerFixture
from unittest.mock import Mock, AsyncMock
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


@pytest.fixture
def async_sleep_mocker(mocker: MockerFixture) -> AsyncMock:
    """Mock asyncio.sleep to speed up tests."""

    async def noop_sleep(t):
        pass

    return mocker.patch('asyncio.sleep', side_effect=noop_sleep)


def test_initialization(timer_mock) -> None:
    assert timer_mock.precision == 4
    assert not timer_mock.verbose

    timer_mock.init(6, True)
    assert timer_mock.precision == 6
    assert timer_mock.verbose


def test_timeit_simple(mock_logger: Mock, mocker: MockerFixture) -> None:
    mock_time = mocker.patch('time.perf_counter_ns', side_effect=[0, int(923_470)])

    timer.init(precision=2)

    @timer.timeit()
    def sample_function():
        return 'result'

    result = sample_function()
    assert result == 'result'
    mock_time.assert_any_call()
    mock_logger.info.assert_called_once_with('sample_function took 923.47μs')


def test_timeit_no_args_kwargs(mock_logger: Mock, mocker: MockerFixture) -> None:
    mock_time = mocker.patch('time.perf_counter_ns', side_effect=[1.0, 1.5])
    timer.init(precision=2, verbose=True)

    @timer.timeit()
    def yet_another_function():
        return 'yet another result'

    result = yet_another_function()
    assert result == 'yet another result'
    mock_time.assert_any_call()
    mock_logger.info.assert_called_once_with('yet_another_function () {} took 0.50ns')


def test_multithreaded_timing(mock_logger: Mock, mocker: MockerFixture) -> None:
    """Test timer works correctly across threads"""
    sim_time_us = 1  # μs
    sim_time_ns = sim_time_us * 1e3
    num_of_threads = 4
    mocker.patch(
        'time.perf_counter_ns',
        side_effect=[0, sim_time_ns] * num_of_threads,
        autospec=True,
    )

    results = []

    @timer.timeit()
    def threaded_operation():
        return threading.get_ident()

    def run_in_thread():
        results.append(threaded_operation())

    threads = [threading.Thread(target=run_in_thread) for _ in range(num_of_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert mock_logger.info.call_count == num_of_threads
    assert len(set(results)) == num_of_threads

    for call_args in mock_logger.info.call_args_list:
        assert f'took {sim_time_us:.{timer.precision}f}μs' in call_args[0][0]


def test_verbose_mode(mock_logger: Mock, mocker: MockerFixture) -> None:
    """Test that verbose mode includes positional and
    keyword arguments in output and preserves the wrapped func result"""
    mocker.patch('time.perf_counter_ns', side_effect=[1e4, 5.23456e4])
    timer.init(verbose=True)

    @timer.timeit()
    def func_with_args(a, b, c=3):
        return a + b + c

    res = func_with_args(1, 2, c=4)
    output = mock_logger.info.call_args[0][0]
    assert '(1, 2)' in output  # checking positional args
    assert "'c': 4" in output  # checking kwargs
    mock_logger.info.assert_called_once_with(
        "func_with_args (1, 2) {'c': 4} took 42.3456μs"
    )
    assert res == 7  # checking returned value preservation


def test_nested_timers(mock_logger: Mock, mocker: MockerFixture) -> None:
    """Test that nested timers work correctly"""
    outer_start = 1000
    inner_start = 1100
    inner_end = 1200
    outer_end = 1300
    mocker.patch(
        'time.perf_counter_ns',
        side_effect=[
            outer_start,
            inner_start,
            inner_end,
            outer_end,
        ],
    )

    @timer.timeit()
    def outer():
        @timer.timeit()
        def inner():
            pass

        return inner()

    outer()

    # Should have two print calls (inner and outer)
    assert mock_logger.info.call_count == 2
    inner_output = mock_logger.info.call_args_list[0][0][0]
    outer_output = mock_logger.info.call_args_list[1][0][0]

    def extract_duration(output: str) -> float:
        match = re.search(r'took\s+([0-9]*\.?[0-9]+)', output)
        if not match:
            raise ValueError(f'Could not parse duration from output: {output}')
        return float(match.group(1))

    inner_duration = extract_duration(inner_output)
    outer_duration = extract_duration(outer_output)

    assert inner_duration == inner_end - inner_start
    assert outer_duration == outer_end - outer_start
    assert outer_duration > inner_duration


def test_unit_scaling(mock_logger: Mock, mocker: MockerFixture) -> None:
    """Test the time unit selection logic directly"""
    boundary_cases = [
        (1e3 - 1, 'ns'),
        (1e3, 'μs'),
        (1e6 - 1, 'μs'),
        (1e6, 'ms'),
        (1e9 - 1, 'ms'),
        (1e9, 's'),
    ]

    for ns, expected_unit in boundary_cases:
        mocker.patch('time.perf_counter_ns', side_effect=[0, ns])
        timer.update({'precision': 2})

        @timer.timeit()
        def dummy():
            pass

        dummy()
        logged_output = mock_logger.info.call_args[0][0]
        assert expected_unit in logged_output, (
            f"Failed for {ns:,}ns → Expected '{expected_unit}' in output. "
            f'Got: {logged_output}'
        )


def test_function_metadata_preserved() -> None:
    """Test that function metadata (name, docstring) is preserved"""
    timer.update({'precision': 3})

    @timer.timeit()
    def dummy_func():
        """Test docstring"""
        pass

    assert dummy_func.__name__ == 'dummy_func'
    assert dummy_func.__doc__ == 'Test docstring'


def test_timeit_with_iterations(mock_logger: Mock, mocker: MockerFixture) -> None:
    k = 3
    sim_times_ns = [0, 1e3, 0, 2e3, 0, 3e3]
    mock_time = mocker.patch(
        'time.perf_counter_ns',
        side_effect=sim_times_ns,
        autospec=True,
    )

    timer.init(precision=2)

    @timer.timeit(iterations=k)
    def sample_function():
        return 'done'

    result = sample_function()

    assert result == 'done'
    mock_time.assert_any_call()

    mock_logger.info.assert_called_once_with(
        f'sample_function took {sum(sim_times_ns) / 3e3:.{timer.precision}f}μs (avg. over {k} runs)'
    )


def test_timeout_single_iteration(mocker: MockerFixture) -> None:
    cfg_timeout_s = 0.1
    duration_s = cfg_timeout_s + 0.1
    current_time_ns = 0.0
    duration_ns = duration_s * 1e9

    mocker.patch(
        'time.perf_counter_ns',
        side_effect=[0.0, duration_ns],
        autospec=True,
    )

    timer.init(6, True)

    @timer.timeit(timeout=cfg_timeout_s)
    def timed_function():
        nonlocal current_time_ns
        current_time_ns += duration_ns

    with pytest.raises(TimeoutError) as exc_info:
        timed_function()

    assert f'took {duration_s:.{timer.precision}f}s' in str(exc_info.value)


def test_timeout_multiple_iterations(mocker: MockerFixture) -> None:
    sim_time_per_iter_s = 0.3
    sim_time_per_iter_ns = sim_time_per_iter_s * 1e9

    k = 5
    timeout_threshold = (k - 1) * sim_time_per_iter_s - 0.1

    mocker.patch(
        'time.perf_counter_ns',
        side_effect=[sim_time_per_iter_ns * count for count in range(2 * k - 1)],
        autospec=True,
    )

    timer.init(6, True)

    @timer.timeit(iterations=k, timeout=timeout_threshold)
    def func(duration: float) -> str:
        return f'{SIM_COMPLETE_TIME} {duration}s'

    with pytest.raises(TimeoutError) as exc_info:
        func(sim_time_per_iter_s)

    expected_timeout_val = f'{timeout_threshold:.{timer.precision}f}s'
    expected_taken_val = f'{(sim_time_per_iter_s * (k - 1)):.{timer.precision}f}s'

    expected_message_template = (
        f'func exceeded {expected_timeout_val} after {k - 1} iterations '
        f'(took {expected_taken_val})'
    )

    assert str(exc_info.value) == expected_message_template


def test_timeout_per_iteration(mocker: MockerFixture) -> None:
    sim_time_s = 0.2
    cfg_timeout = 0.1
    mocker.patch(
        'time.perf_counter_ns', side_effect=[0.0, sim_time_s * 1e9], autospec=True
    )

    timer.init(6, True)

    @timer.timeit(iterations=5, timeout=cfg_timeout, per_iteration=True)
    def func(duration: float) -> str:
        return f'{SIM_COMPLETE_TIME} {duration}s'

    with pytest.raises(TimeoutError) as exc_info:
        func(sim_time_s)

    assert (
        f'exceeded {cfg_timeout:.{timer.precision}f}s on iteration 1 '
        f'(took {sim_time_s:.{timer.precision}f}s)'
    ) in str(exc_info.value)


def test_timeout_with_fast_function(mock_logger: Mock, mocker: MockerFixture) -> None:
    sim_time_ms = 50.1
    sim_time_s = sim_time_ms / 1e3

    mocker.patch(
        'time.perf_counter_ns', side_effect=[0, sim_time_ms * 1e6], autospec=True
    )

    timer.init()

    @timer.timeit(timeout=1.0)
    def func(duration: float) -> str:
        return f'{SIM_COMPLETE_TIME} {duration}s'

    result = func(sim_time_s)

    mock_logger.info.assert_called_once_with(
        f'func took {sim_time_ms:.{timer.precision}f}ms'
    )
    assert result == f'{SIM_COMPLETE_TIME} {sim_time_s}s'


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


# Test nanoseconds
def test_nanoseconds_whole_number(timer_mock: Timer) -> None:
    """Test whole number nanoseconds"""
    assert timer_mock._duration_formatter(150) == '150.00ns'
    assert timer_mock._duration_formatter(1) == '1.00ns'
    assert timer_mock._duration_formatter(999) == '999.00ns'


def test_nanoseconds_zero(timer_mock: Timer) -> None:
    """Test zero nanoseconds"""
    assert timer_mock._duration_formatter(0) == '0.00ns'


def test_microseconds_precision_default(timer_mock: Timer) -> None:
    """Test microseconds with default precision"""
    assert timer_mock._duration_formatter(1500) == '1.5000μs'
    assert timer_mock._duration_formatter(123456) == '123.4560μs'
    assert timer_mock._duration_formatter(999999) == '999.9990μs'


def test_microseconds_custom_precision(timer_mock: Timer) -> None:
    """Test microseconds with custom precision"""
    assert timer_mock._duration_formatter(1500, precision=2) == '1.50μs'
    assert timer_mock._duration_formatter(123456, precision=0) == '123μs'
    assert timer_mock._duration_formatter(123456, precision=6) == '123.456000μs'


def test_microseconds_boundary(timer_mock: Timer) -> None:
    """Test microsecond boundaries"""
    assert timer_mock._duration_formatter(999) == '999.00ns'
    assert timer_mock._duration_formatter(1000) == '1.0000μs'
    assert timer_mock._duration_formatter(999999) == '999.9990μs'


def test_milliseconds_precision_default(timer_mock: Timer) -> None:
    """Test milliseconds with default precision"""
    assert timer_mock._duration_formatter(1500000) == '1.5000ms'
    assert timer_mock._duration_formatter(123456789) == '123.4568ms'
    assert timer_mock._duration_formatter(999999000) == '999.9990ms'
    assert timer_mock._duration_formatter(999999999) == '1000.0000ms'


def test_milliseconds_boundary(timer_mock: Timer) -> None:
    """Test millisecond boundaries"""
    assert timer_mock._duration_formatter(999999) == '999.9990μs'
    assert timer_mock._duration_formatter(1000000) == '1.0000ms'
    assert timer_mock._duration_formatter(999999000) == '999.9990ms'
    assert timer_mock._duration_formatter(999999999) == '1000.0000ms'


def test_milliseconds_rounding_behavior(timer_mock: Timer) -> None:
    """Test milliseconds rounding behavior at boundaries"""
    assert timer_mock._duration_formatter(999999499) == '999.9995ms'
    assert timer_mock._duration_formatter(999999500) == '999.9995ms'
    assert timer_mock._duration_formatter(999999999) == '1000.0000ms'
    assert timer_mock._duration_formatter(1000000000) == '1.0s'


def test_hours_with_minutes_and_seconds(timer_mock: Timer) -> None:
    """Test hours with minutes and seconds"""
    assert timer_mock._duration_formatter(3661000000000) == '1h 1m 1s'
    assert timer_mock._duration_formatter(7322000000000) == '2h 2m 2s'
    assert timer_mock._duration_formatter(7205000000000) == '2h 5s'


def test_hours_with_minutes_only(timer_mock: Timer) -> None:
    """Test hours with minutes only"""
    assert timer_mock._duration_formatter(3660000000000) == '1h 1m'
    assert timer_mock._duration_formatter(7200000000000) == '2h'


def test_hours_with_seconds_only(timer_mock: Timer) -> None:
    """Test hours with seconds only"""
    assert timer_mock._duration_formatter(3605000000000) == '1h 5s'


def test_hours_only(timer_mock: Timer) -> None:
    """Test hours without minutes or seconds"""
    assert timer_mock._duration_formatter(3600000000000) == '1h'
    assert timer_mock._duration_formatter(7200000000000) == '2h'


@pytest.mark.parametrize(
    'ns_input,expected_output,precision',
    [
        (0, '0.00ns', 4),
        (1, '1.00ns', 4),
        (999, '999.00ns', 4),
        (1000, '1.0000μs', 4),
        (1500, '1.5000μs', 4),
        (999999, '999.9990μs', 4),
        (1000000, '1.0000ms', 4),
        (1500000, '1.5000ms', 4),
        (999999000, '999.9990ms', 4),
        (999999999, '1000.0000ms', 4),
        (1000000000, '1.0s', 4),
        (1500000000, '1.5s', 4),
        (10000000000, '10s', 4),
        (60000000000, '1m', 4),
        (65000000000, '1m 5s', 4),
        (3600000000000, '1h', 4),
        (3661000000000, '1h 1m 1s', 4),
        (7205000000000, '2h 5s', 4),  # Fixed: no zero minutes
    ],
)
def test_parameterized(
    timer_mock: Timer, ns_input: float, expected_output: str, precision: int
) -> None:
    """Parameterized test covering all major cases"""
    result = timer_mock._duration_formatter(ns_input, precision)
    assert result == expected_output


def test_comprehensive_hour_decomposition(timer_mock: Timer) -> None:
    """Test all variations of hour-minute-second decomposition"""
    assert timer_mock._duration_formatter(3600000000000) == '1h'
    assert timer_mock._duration_formatter(7200000000000) == '2h'
    assert timer_mock._duration_formatter(3660000000000) == '1h 1m'
    assert timer_mock._duration_formatter(7320000000000) == '2h 2m'
    assert timer_mock._duration_formatter(3605000000000) == '1h 5s'
    assert timer_mock._duration_formatter(7210000000000) == '2h 10s'
    assert timer_mock._duration_formatter(3661000000000) == '1h 1m 1s'
    assert timer_mock._duration_formatter(7322000000000) == '2h 2m 2s'
    assert timer_mock._duration_formatter(7205000000000) == '2h 5s'


def test_format_duration_in_decorator_context(
    timer_mock: Timer, mock_logger: Mock
) -> None:
    """Test that format_duration works in a decorator-like context"""
    test_cases = [
        (150, '150.00ns'),
        (1500000, '1.5000ms'),
        (1000000000, '1.0s'),
        (65000000000, '1m 5s'),
    ]

    for elapsed_ns, expected in test_cases:
        result = timer_mock._duration_formatter(elapsed_ns)
        assert result == expected

    mock_logger.info.assert_not_called()


def test_precision_propagation(timer_mock: Timer) -> None:
    """Test that precision is properly propagated through formatting"""
    ns_value = 1234567

    assert timer_mock._duration_formatter(ns_value, precision=2) == '1.23ms'
    assert timer_mock._duration_formatter(ns_value, precision=4) == '1.2346ms'
    assert timer_mock._duration_formatter(ns_value, precision=6) == '1.234567ms'

import threading
import pytest
import re

from pytest_mock import MockerFixture
from unittest.mock import Mock

from .test_timers_common import (
    timer,
    timer_mock,  # noqa: F401
    mock_logger,  # noqa: F401
    SIM_COMPLETE_TIME,
)


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

import threading
import time
import pytest
from src.nano_dev_utils.timers import Timer


def test_initialization():
    timer = Timer()
    assert timer.precision == 4
    assert not timer.verbose

    timer_custom = Timer(precision=6, verbose=True)
    assert timer_custom.precision == 6
    assert timer_custom.verbose


def long_running_function(duration: float) -> None:
    time.sleep(duration)


def test_timeit_simple(mocker):
    mock_print = mocker.patch('builtins.print')
    mock_time = mocker.patch('time.perf_counter_ns', side_effect=[0, 9.23467e5])
    timer = Timer(precision=2)

    @timer.timeit()
    def sample_function():
        return 'result'

    result = sample_function()
    assert result == 'result'
    mock_time.assert_any_call()
    mock_print.assert_called_once_with('sample_function took 923.47 [μs]')


def test_timeit_no_args_kwargs(mocker):
    mock_print = mocker.patch('builtins.print')
    mock_time = mocker.patch('time.perf_counter_ns', side_effect=[1.0, 1.5])
    timer = Timer(precision=2, verbose=True)

    @timer.timeit()
    def yet_another_function():
        return 'yet another result'

    result = yet_another_function()
    assert result == 'yet another result'
    mock_time.assert_any_call()
    mock_print.assert_called_once_with('yet_another_function () {} took 0.50 [ns]')


def test_multithreaded_timing(mocker):
    """Test timer works correctly across threads"""
    mock_print = mocker.patch('builtins.print')
    timer = Timer()
    results = []

    @timer.timeit()
    def threaded_operation():
        time.sleep(0.1)
        return threading.get_ident()

    def run_in_thread():
        results.append(threaded_operation())

    threads = [threading.Thread(target=run_in_thread) for _ in range(3)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Should have 3 print calls (one per thread)
    assert mock_print.call_count == 3
    # All thread IDs should be different
    assert len(set(results)) == 3


def test_verbose_mode(mocker):
    """Test that verbose mode includes positional and
    keyword arguments in output and preserves the wrapped func result"""
    mock_print = mocker.patch('builtins.print')
    mocker.patch('time.perf_counter_ns', side_effect=[1e4, 5.23456e4])
    verbose_timer = Timer(verbose=True)

    @verbose_timer.timeit()
    def func_with_args(a, b, c=3):
        return a + b + c

    res = func_with_args(1, 2, c=4)
    output = mock_print.call_args[0][0]
    assert '(1, 2)' in output  # checking positional args
    assert "'c': 4" in output  # checking kwargs
    mock_print.assert_called_once_with(
        "func_with_args (1, 2) {'c': 4} took 42.3456 [μs]"
    )
    assert res == 7  # checking returned value preservation


def test_nested_timers(mocker):
    """Test that nested timers work correctly"""
    mock_print = mocker.patch('builtins.print')
    timer = Timer()

    @timer.timeit()
    def outer():
        @timer.timeit()
        def inner():
            time.sleep(0.1)

        return inner()

    outer()

    # Should have two print calls (inner and outer)
    assert mock_print.call_count == 2
    inner_output = mock_print.call_args_list[0][0][0]
    outer_output = mock_print.call_args_list[1][0][0]

    inner_time = float(inner_output.split('took ')[1].split(' [')[0])
    outer_time = float(outer_output.split('took ')[1].split(' [')[0])

    assert outer_time > inner_time


def test_unit_scaling(mocker):
    """Test the time unit selection logic directly"""
    mock_print = mocker.patch('builtins.print')

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
        timer = Timer(precision=2)

        @timer.timeit()
        def dummy():
            pass

        dummy()
        printed_output = mock_print.call_args[0][0]
        assert expected_unit in printed_output, (
            f"Failed for {ns:,}ns → Expected '{expected_unit}' in output. "
            f'Got: {printed_output}'
        )


def test_function_metadata_preserved():
    """Test that function metadata (name, docstring) is preserved"""
    timer = Timer(precision=3)

    @timer.timeit()
    def dummy_func():
        """Test docstring"""
        pass

    assert dummy_func.__name__ == 'dummy_func'
    assert dummy_func.__doc__ == 'Test docstring'


def test_timeit_with_iterations(mocker):
    mock_print = mocker.patch('builtins.print')
    mock_time = mocker.patch(
        'time.perf_counter_ns', side_effect=[0, 1000, 0, 2000, 0, 3000]
    )

    timer = Timer(precision=2)

    @timer.timeit(iterations=3)
    def sample_function():
        return 'done'

    result = sample_function()

    assert result == 'done'
    mock_time.assert_any_call()

    mock_print.assert_called_once_with(
        'sample_function took 2.00 [μs] (avg. over 3 runs)'
    )


def test_timeout_single_iteration(mocker):
    mock_perf_counter = mocker.patch('time.perf_counter', autospec=True)
    current_time_s = 0.0
    mock_perf_counter.side_effect = lambda: current_time_s
    timer = Timer(precision=6, verbose=True)

    @timer.timeit(timeout=0.1)
    def timed_function():
        nonlocal current_time_s
        current_time_s += 0.20  # Simulate 0.2 seconds passing

    with pytest.raises(TimeoutError) as exc_info:
        timed_function()

    assert "took 0.20s" in str(exc_info.value)


def test_timeout_multiple_iterations():
    timer = Timer(precision=6, verbose=True)

    # Set a timeout of 0.5s for the total execution of 3 iterations
    with pytest.raises(TimeoutError):
        timed_function = timer.timeit(iterations=3, timeout=0.5)(long_running_function)
        timed_function(0.3)  # Each iteration takes 0.3s, so total should exceed 0.5s


def test_timeout_per_iteration():
    timer = Timer(precision=6, verbose=True)

    # Set a timeout of 0.1s per iteration
    with pytest.raises(TimeoutError):
        timed_function = timer.timeit(iterations=5, timeout=0.1, per_iteration=True)(long_running_function)
        timed_function(0.2)  # Each iteration will exceed the 0.1s timeout


def test_timeout_with_fast_function():
    timer = Timer(precision=6, verbose=True)

    # Test a fast function (should not raise TimeoutError)
    timed_function = timer.timeit(timeout=1.0)(long_running_function)
    timed_function(0.05)

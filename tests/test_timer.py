from unittest.mock import patch
import threading
import time
from src.nano_dev_utils.timers import Timer


def test_initialization():
    timer = Timer()
    assert timer.precision == 4
    assert not timer.verbose

    timer_custom = Timer(precision=6, verbose=True)
    assert timer_custom.precision == 6
    assert timer_custom.verbose


@patch('time.perf_counter_ns')
@patch('builtins.print')
def test_timeit_simple(mock_print, mock_perf_counter_ns):
    mock_perf_counter_ns.side_effect = [0, 9.23467e5]
    timer = Timer(precision=2)

    @timer.timeit
    def sample_function():
        return 'result'

    result = sample_function()
    assert result == 'result'
    mock_perf_counter_ns.assert_any_call()
    mock_print.assert_called_once_with('sample_function took 923.47 [μs]')


@patch('time.perf_counter_ns')
@patch('builtins.print')
def test_timeit_no_args_kwargs(mock_print, mock_perf_counter_ns):
    mock_perf_counter_ns.side_effect = [1.0, 1.5]
    timer = Timer(precision=2, verbose=True)

    @timer.timeit
    def yet_another_function():
        return 'yet another result'

    result = yet_another_function()
    assert result == 'yet another result'
    mock_perf_counter_ns.assert_any_call()
    mock_print.assert_called_once_with('yet_another_function () {} took 0.50 [ns]')


@patch('builtins.print')
def test_multithreaded_timing(mock_print):
    """Test timer works correctly across threads"""
    timer = Timer()
    results = []

    @timer.timeit
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


@patch('time.perf_counter_ns')
@patch('builtins.print')
def test_verbose_mode(mock_print, mock_perf_counter_ns):
    """Test that verbose mode includes positional and
    keyword arguments in output and preserves the wrapped func result"""
    mock_perf_counter_ns.side_effect = [1e4, 5.23456e4]
    verbose_timer = Timer(verbose=True)

    @verbose_timer.timeit
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


@patch('builtins.print')
def test_nested_timers(mock_print):
    """Test that nested timers work correctly"""
    timer = Timer()

    @timer.timeit
    def outer():
        @timer.timeit
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


@patch('time.perf_counter_ns')
@patch('builtins.print')
def test_unit_scaling_logic(mock_print, mock_perf_counter_ns):
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
        mock_perf_counter_ns.side_effect = [0, ns]
        timer = Timer(precision=2)

        @timer.timeit
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

    @timer.timeit
    def dummy_func():
        """Test docstring"""
        pass

    assert dummy_func.__name__ == 'dummy_func'
    assert dummy_func.__doc__ == 'Test docstring'

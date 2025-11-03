import pytest
from unittest.mock import Mock

from nano_dev_utils.timers import NS_IN_US, NS_IN_MS, NS_IN_SEC, NS_IN_MIN, NS_IN_HOUR


def test_nanoseconds_whole_number(res_form_mock) -> None:
    """Test whole number nanoseconds"""
    assert res_form_mock(150) == '150.0000 ns'
    assert res_form_mock(1) == '1.0000 ns'
    assert res_form_mock(999) == '999.0000 ns'


def test_nanoseconds_zero(res_form_mock) -> None:
    """Test zero nanoseconds"""
    assert res_form_mock(0) == '0.0000 ns'


def test_microseconds_precision_default(res_form_mock) -> None:
    """Test microseconds with default precision"""
    assert res_form_mock(1500) == '1.5000 μs'
    assert res_form_mock(123456) == '123.4560 μs'
    assert res_form_mock(NS_IN_MS - 1) == '999.9990 μs'


def test_microseconds_custom_precision(res_form_mock) -> None:
    """Test microseconds with custom precision"""
    assert res_form_mock(1500, precision=2) == '1.50 μs'
    assert res_form_mock(123456, precision=0) == '123 μs'
    assert res_form_mock(123456, precision=6) == '123.456000 μs'


def test_microseconds_boundary(res_form_mock) -> None:
    """Test microsecond boundaries"""
    assert res_form_mock(NS_IN_US - 1) == '999.0000 ns'
    assert res_form_mock(NS_IN_US) == '1.0000 μs'
    assert res_form_mock(NS_IN_MS - 1) == '999.9990 μs'


def test_milliseconds_precision_default(res_form_mock) -> None:
    """Test milliseconds with default precision"""
    assert res_form_mock(1_500 * NS_IN_US) == '1.5000 ms'
    assert res_form_mock(123_456_789) == '123.4568 ms'
    assert res_form_mock(NS_IN_SEC - 1000) == '999.9990 ms'
    assert res_form_mock(NS_IN_SEC - 1) == '1000.0000 ms'


def test_milliseconds_boundary(res_form_mock) -> None:
    """Test millisecond boundaries"""
    assert res_form_mock(NS_IN_MS - 1) == '999.9990 μs'
    assert res_form_mock(NS_IN_MS) == '1.0000 ms'
    assert res_form_mock(NS_IN_SEC - 1000) == '999.9990 ms'
    assert res_form_mock(NS_IN_SEC - 1) == '1000.0000 ms'


def test_milliseconds_rounding_behavior(res_form_mock) -> None:
    """Test milliseconds rounding behavior at boundaries"""
    assert res_form_mock(NS_IN_SEC - 501) == '999.9995 ms'
    assert res_form_mock(NS_IN_SEC - 500) == '999.9995 ms'
    assert res_form_mock(NS_IN_SEC - 1) == '1000.0000 ms'
    assert res_form_mock(NS_IN_SEC) == '1.0000 s'


def test_hours_with_minutes_and_seconds(res_form_mock) -> None:
    """Test hours with minutes and seconds"""
    assert res_form_mock(NS_IN_HOUR + NS_IN_MIN + NS_IN_SEC) == '1 h 1 m 1 s'
    assert res_form_mock(2 * NS_IN_HOUR + 2 * NS_IN_MIN + 2 * NS_IN_SEC) == '2 h 2 m 2 s'
    assert res_form_mock(2 * NS_IN_HOUR + 5 * NS_IN_SEC) == '2 h 5 s'


def test_hours_with_minutes_only(res_form_mock) -> None:
    """Test hours with minutes only"""
    assert res_form_mock(NS_IN_HOUR + NS_IN_MIN) == '1 h 1 m'
    assert res_form_mock(2 * NS_IN_HOUR) == '2 h'


def test_hours_with_seconds_only(res_form_mock) -> None:
    """Test hours with seconds only"""
    assert res_form_mock(NS_IN_HOUR + 5 * NS_IN_SEC) == '1 h 5 s'


def test_hours_only(res_form_mock) -> None:
    """Test hours without minutes or seconds"""
    assert res_form_mock(NS_IN_HOUR) == '1 h'
    assert res_form_mock(2 * NS_IN_HOUR) == '2 h'


@pytest.mark.parametrize(
    'ns_input,expected_output,precision',
    [
        (0, '0.0000 ns', 4),
        (1, '1.0000 ns', 4),
        (NS_IN_US - 1, '999.0000 ns', 4),
        (NS_IN_US, '1.0000 μs', 4),
        (1_500, '1.5000 μs', 4),
        (NS_IN_MS - 1, '999.9990 μs', 4),
        (NS_IN_MS, '1.0000 ms', 4),
        (1_500 * NS_IN_US, '1.5000 ms', 4),
        (NS_IN_SEC - 1000, '999.9990 ms', 4),
        (NS_IN_SEC - 1, '1000.0000 ms', 4),
        (NS_IN_SEC, '1.0000 s', 4),
        (1.5 * NS_IN_SEC, '1.5000 s', 4),
        (10 * NS_IN_SEC, '10.0000 s', 4),
        (NS_IN_MIN, '1 m', 4),
        (NS_IN_MIN + 5 * NS_IN_SEC, '1 m 5 s', 4),
        (NS_IN_HOUR, '1 h', 4),
        (NS_IN_HOUR + NS_IN_MIN + NS_IN_SEC, '1 h 1 m 1 s', 4),
        (2 * NS_IN_HOUR + 5 * NS_IN_SEC, '2 h 5 s', 4),
    ],
)
def test_parameterized(
    res_form_mock, ns_input: float, expected_output: str, precision: int
) -> None:
    """Parameterized test covering all major cases"""
    result = res_form_mock(ns_input, precision=precision)
    assert result == expected_output


def test_comprehensive_hour_decomposition(res_form_mock) -> None:
    """Test all variations of hour-minute-second decomposition"""
    assert res_form_mock(NS_IN_HOUR) == '1 h'
    assert res_form_mock(2 * NS_IN_HOUR) == '2 h'
    assert res_form_mock(NS_IN_HOUR + NS_IN_MIN) == '1 h 1 m'
    assert res_form_mock(2 * NS_IN_HOUR + 2 * NS_IN_MIN) == '2 h 2 m'
    assert res_form_mock(NS_IN_HOUR + 5 * NS_IN_SEC) == '1 h 5 s'
    assert res_form_mock(2 * NS_IN_HOUR + 10 * NS_IN_SEC) == '2 h 10 s'
    assert res_form_mock(NS_IN_HOUR + NS_IN_MIN + NS_IN_SEC) == '1 h 1 m 1 s'
    assert res_form_mock(2 * NS_IN_HOUR + 2 * NS_IN_MIN + 2 * NS_IN_SEC) == '2 h 2 m 2 s'
    assert res_form_mock(2 * NS_IN_HOUR + 5 * NS_IN_SEC) == '2 h 5 s'


def test_format_duration_in_decorator_context(res_form_mock, mock_logger: Mock) -> None:
    """Test that format_duration works in a decorator-like context"""
    test_cases = [
        (150.0004, '150.0004 ns'),
        (1_500 * NS_IN_US + 0.24 * NS_IN_US, '1.5002 ms'),  # intended by precision
        (NS_IN_SEC + 3.250001 * NS_IN_MS, '1.0033 s'),  # ditto
        (NS_IN_MIN + 5 * NS_IN_SEC, '1 m 5 s'),
    ]

    for elapsed_ns, expected in test_cases:
        result = res_form_mock(elapsed_ns)
        assert result == expected

    mock_logger.info.assert_not_called()


def test_precision_propagation(res_form_mock) -> None:
    """Test that precision is properly propagated through formatting"""
    ns_value = 1234567

    assert res_form_mock(ns_value, precision=2) == '1.23 ms'
    assert res_form_mock(ns_value, precision=4) == '1.2346 ms'
    assert res_form_mock(ns_value, precision=6) == '1.234567 ms'

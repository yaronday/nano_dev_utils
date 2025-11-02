import pytest
from unittest.mock import Mock


def test_nanoseconds_whole_number(res_form_mock) -> None:
    """Test whole number nanoseconds"""
    assert res_form_mock(150) == '150.00ns'
    assert res_form_mock(1) == '1.00ns'
    assert res_form_mock(999) == '999.00ns'


def test_nanoseconds_zero(res_form_mock) -> None:
    """Test zero nanoseconds"""
    assert res_form_mock(0) == '0.00ns'


def test_microseconds_precision_default(res_form_mock) -> None:
    """Test microseconds with default precision"""
    assert res_form_mock(1500) == '1.5000μs'
    assert res_form_mock(123456) == '123.4560μs'
    assert res_form_mock(999999) == '999.9990μs'


def test_microseconds_custom_precision(res_form_mock) -> None:
    """Test microseconds with custom precision"""
    assert res_form_mock(1500, precision=2) == '1.50μs'
    assert res_form_mock(123456, precision=0) == '123μs'
    assert res_form_mock(123456, precision=6) == '123.456000μs'


def test_microseconds_boundary(res_form_mock) -> None:
    """Test microsecond boundaries"""
    assert res_form_mock(999) == '999.00ns'
    assert res_form_mock(1000) == '1.0000μs'
    assert res_form_mock(999999) == '999.9990μs'


def test_milliseconds_precision_default(res_form_mock) -> None:
    """Test milliseconds with default precision"""
    assert res_form_mock(1500000) == '1.5000ms'
    assert res_form_mock(123456789) == '123.4568ms'
    assert res_form_mock(999999000) == '999.9990ms'
    assert res_form_mock(999999999) == '1000.0000ms'


def test_milliseconds_boundary(res_form_mock) -> None:
    """Test millisecond boundaries"""
    assert res_form_mock(999999) == '999.9990μs'
    assert res_form_mock(1000000) == '1.0000ms'
    assert res_form_mock(999999000) == '999.9990ms'
    assert res_form_mock(999999999) == '1000.0000ms'


def test_milliseconds_rounding_behavior(res_form_mock) -> None:
    """Test milliseconds rounding behavior at boundaries"""
    assert res_form_mock(999999499) == '999.9995ms'
    assert res_form_mock(999999500) == '999.9995ms'
    assert res_form_mock(999999999) == '1000.0000ms'
    assert res_form_mock(1000000000) == '1.0s'


def test_hours_with_minutes_and_seconds(res_form_mock) -> None:
    """Test hours with minutes and seconds"""
    assert res_form_mock(3661000000000) == '1h 1m 1s'
    assert res_form_mock(7322000000000) == '2h 2m 2s'
    assert res_form_mock(7205000000000) == '2h 5s'


def test_hours_with_minutes_only(res_form_mock) -> None:
    """Test hours with minutes only"""
    assert res_form_mock(3660000000000) == '1h 1m'
    assert res_form_mock(7200000000000) == '2h'


def test_hours_with_seconds_only(res_form_mock) -> None:
    """Test hours with seconds only"""
    assert res_form_mock(3605000000000) == '1h 5s'


def test_hours_only(res_form_mock) -> None:
    """Test hours without minutes or seconds"""
    assert res_form_mock(3600000000000) == '1h'
    assert res_form_mock(7200000000000) == '2h'


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
    res_form_mock, ns_input: float, expected_output: str, precision: int
) -> None:
    """Parameterized test covering all major cases"""
    result = res_form_mock(ns_input, precision)
    assert result == expected_output


def test_comprehensive_hour_decomposition(res_form_mock) -> None:
    """Test all variations of hour-minute-second decomposition"""
    assert res_form_mock(3600000000000) == '1h'
    assert res_form_mock(7200000000000) == '2h'
    assert res_form_mock(3660000000000) == '1h 1m'
    assert res_form_mock(7320000000000) == '2h 2m'
    assert res_form_mock(3605000000000) == '1h 5s'
    assert res_form_mock(7210000000000) == '2h 10s'
    assert res_form_mock(3661000000000) == '1h 1m 1s'
    assert res_form_mock(7322000000000) == '2h 2m 2s'
    assert res_form_mock(7205000000000) == '2h 5s'


def test_format_duration_in_decorator_context(
    res_form_mock, mock_logger: Mock
) -> None:
    """Test that format_duration works in a decorator-like context"""
    test_cases = [
        (150, '150.00ns'),
        (1500000, '1.5000ms'),
        (1000000000, '1.0s'),
        (65000000000, '1m 5s'),
    ]

    for elapsed_ns, expected in test_cases:
        result = res_form_mock(elapsed_ns)
        assert result == expected

    mock_logger.info.assert_not_called()


def test_precision_propagation(res_form_mock) -> None:
    """Test that precision is properly propagated through formatting"""
    ns_value = 1234567

    assert res_form_mock(ns_value, precision=2) == '1.23ms'
    assert res_form_mock(ns_value, precision=4) == '1.2346ms'
    assert res_form_mock(ns_value, precision=6) == '1.234567ms'

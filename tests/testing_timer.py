import unittest
from unittest.mock import patch
from src.nano_utils_yaronday.timers import Timer


class TestTimer(unittest.TestCase):

    def test_initialization(self):
        timer = Timer()
        self.assertEqual(timer.precision, 4)
        self.assertFalse(timer.verbose)
        self.assertEqual(timer.timing_records, [])

        timer_custom = Timer(precision=6, verbose=True)
        self.assertEqual(timer_custom.precision, 6)
        self.assertTrue(timer_custom.verbose)
        self.assertEqual(timer_custom.timing_records, [])

    def test_record_timing(self):
        timer = Timer(precision=3)
        timer.record_timing(1.23456)
        self.assertEqual(timer.timing_records, ['1.235'])
        timer.record_timing(0.00789)
        self.assertEqual(timer.timing_records, ['1.235', '0.008'])

    def test_get_timing_records(self):
        timer = Timer()
        timer.record_timing(0.5)
        timer.record_timing(1.0)
        records = timer.get_timing_records()
        self.assertEqual(records, ['0.5000', '1.0000'])

    @patch('time.perf_counter')
    @patch('builtins.print')
    def test_timeit_simple(self, mock_print, mock_perf_counter):
        mock_perf_counter.side_effect = [0, 0.12345]
        timer = Timer(precision=5)

        @timer.timeit
        def sample_function():
            return "result"

        result = sample_function()
        self.assertEqual(result, "result")
        mock_perf_counter.assert_any_call()
        mock_print.assert_called_once_with('sample_function took 0.12345 [s]')

    @patch('time.perf_counter')
    @patch('builtins.print')
    def test_timeit_verbose(self, mock_print, mock_perf_counter):
        mock_perf_counter.side_effect = [0, 0.56789]
        timer = Timer(precision=3, verbose=True)

        @timer.timeit
        def another_function(arg1, kwarg1=None):
            return "another result"

        result = another_function(10, kwarg1="hello")
        self.assertEqual(result, "another result")
        mock_perf_counter.assert_any_call()
        mock_print.assert_called_once_with("another_function (10,) {'kwarg1': 'hello'} took 0.568 [s]")

    @patch('time.perf_counter')
    @patch('builtins.print')
    def test_timeit_no_args_kwargs(self, mock_print, mock_perf_counter):
        mock_perf_counter.side_effect = [1.0, 1.5]
        timer = Timer(precision=2, verbose=True)

        @timer.timeit
        def yet_another_function():
            return "yet another result"

        result = yet_another_function()
        self.assertEqual(result, "yet another result")
        mock_perf_counter.assert_any_call()
        mock_print.assert_called_once_with("yet_another_function () {} took 0.50 [s]")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

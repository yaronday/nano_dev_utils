from functools import wraps
import time


class Timer:
    def __init__(self, precision=4, verbose=False):
        self.timing_records = []
        self.precision = precision
        self.verbose = verbose

    def record_timing(self, duration):
        self.timing_records.append(f'{duration:.{self.precision}f}')

    def get_timing_records(self):
        return self.timing_records

    def timeit(self, func):
        @wraps(func)
        def timeit_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            total_time = end_time - start_time
            extra_info = f'{args} {kwargs} ' if self.verbose else ''
            print(f'{func.__name__} {extra_info}took {total_time:.{self.precision}f} [s]')
            return result
        return timeit_wrapper





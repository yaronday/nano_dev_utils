from functools import wraps
import time


class Timer:
    def __init__(self, precision=4, verbose=False):
        self.precision = precision
        self.verbose = verbose

    def timeit(self, func):
        @wraps(func)
        def timeit_wrapper(*args, **kwargs):
            start_time = time.perf_counter_ns()
            result = func(*args, **kwargs)
            end_time = time.perf_counter_ns()
            total_ns = end_time - start_time

            if total_ns < 1_000:  # 1μs
                value = total_ns
                unit = "ns"
            elif total_ns < 1_000_000:  # < 1ms
                value = total_ns / 1_000
                unit = "μs"
            elif total_ns < 1_000_000_000:  # < 1s
                value = total_ns / 1_000_000
                unit = "ms"
            else:
                value = total_ns / 1_000_000_000
                unit = "s"

            extra_info = f'{args} {kwargs} ' if self.verbose else ''
            print(f'{func.__name__} {extra_info}took {value:.{self.precision}f} [{unit}]')
            return result

        return timeit_wrapper

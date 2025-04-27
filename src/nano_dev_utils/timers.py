from functools import wraps
import time
from typing import Callable, ParamSpec, TypeVar
P = ParamSpec('P')
R = TypeVar('R')


class Timer:
    def __init__(self, precision=4, verbose=False):
        self.precision = precision
        self.verbose = verbose
        self.units = [
            (1e9, 's'),
            (1e6, 'ms'),
            (1e3, 'μs'),
            (1.0, 'ns')
        ]

    def timeit(self, func: Callable[P, R]) -> Callable[P, R]:
        """Decorator that times function execution with automatic unit scaling."""
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter_ns()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter_ns() - start

            value = elapsed
            unit = 'ns'

            for divisor, unit in self.units:
                if elapsed >= divisor or unit == 'ns':
                    value = elapsed / divisor
                    break

            extra_info = f'{args} {kwargs} ' if self.verbose else ''
            print(f'{func.__name__} {extra_info}took {value:.{self.precision}f} [{unit}]')
            return result

        return wrapper

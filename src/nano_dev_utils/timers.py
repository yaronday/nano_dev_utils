from functools import wraps
import time
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec('P')
R = TypeVar('R')


class Timer:
    def __init__(self, precision=4, verbose=False):
        self.precision = precision
        self.verbose = verbose
        self.units = [(1e9, 's'), (1e6, 'ms'), (1e3, 'μs'), (1.0, 'ns')]

    def timeit(
        self, iterations: int = 1
    ) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
        def decorator(func: Callable[P, R]) -> Callable[P, R | None]:
            """Decorator that times function execution with automatic unit scaling and averaging."""

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
                total_elapsed = 0
                result = None

                for _ in range(iterations):
                    start = time.perf_counter_ns()
                    result = func(*args, **kwargs)
                    total_elapsed += time.perf_counter_ns() - start

                avg_elapsed = total_elapsed / iterations
                value = avg_elapsed
                unit = 'ns'

                for divisor, unit in self.units:
                    if avg_elapsed >= divisor or unit == 'ns':
                        value = avg_elapsed / divisor
                        break

                extra_info = f'{args} {kwargs} ' if self.verbose else ''
                iter_info = f' (avg over {iterations} runs)' if iterations > 1 else ''
                print(
                    f'{func.__name__} {extra_info}took {value:.{self.precision}f} [{unit}]{iter_info}'
                )
                return result

            return wrapper

        return decorator

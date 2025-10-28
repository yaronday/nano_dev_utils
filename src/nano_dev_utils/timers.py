from functools import wraps
import time
import logging
from typing import Callable, ParamSpec, TypeVar

from nano_dev_utils.common import update

lgr = logging.getLogger(__name__)
"""Module-level logger. Configure using logging.basicConfig() in your application."""

P = ParamSpec('P')
R = TypeVar('R')


class Timer:
    def __init__(self, precision: int = 4, verbose: bool = False):
        self.precision = precision
        self.verbose = verbose
        self.units = [(1e9, 's'), (1e6, 'ms'), (1e3, 'μs'), (1.0, 'ns')]

    def init(self, *args, **kwargs) -> None:
        self.__init__(*args, **kwargs)

    def update(self, attrs: dict) -> None:
        update(self, attrs)

    def timeit(
        self,
        iterations: int = 1,
        timeout: float | None = None,
        per_iteration: bool = False,
    ) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
        """Decorator that times function execution with optional timeout support."""

        def decorator(func: Callable[P, R]) -> Callable[P, R | None]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
                total_elapsed_ns = 0
                result: R | None = None

                for i in range(1, iterations + 1):
                    start_ns = time.perf_counter_ns()
                    result = func(*args, **kwargs)
                    duration_ns = time.perf_counter_ns() - start_ns
                    total_elapsed_ns += duration_ns

                    if timeout is not None:
                        if per_iteration:
                            duration_s = duration_ns / 1e9
                            if duration_s > timeout:
                                raise TimeoutError(
                                    f'{func.__name__} exceeded '
                                    f'{timeout:.{self.precision}f}s on '
                                    f'iteration {i} (took '
                                    f'{duration_s:.{self.precision}f}s)'
                                )
                        else:
                            total_duration_s = total_elapsed_ns / 1e9
                            if total_duration_s > timeout:
                                raise TimeoutError(
                                    f'{func.__name__} exceeded {timeout:.{self.precision}f}s '
                                    f'after {i} iterations (took {total_duration_s:.{self.precision}f}s)'
                                )

                avg_elapsed_ns = total_elapsed_ns / iterations
                value, unit = next(
                    (avg_elapsed_ns / div, u)
                    for div, u in self.units
                    if avg_elapsed_ns >= div or u == 'ns'
                )
                extra_info = f'{args} {kwargs} ' if self.verbose else ''
                iter_info = f' (avg. over {iterations} runs)' if iterations > 1 else ''
                lgr.info(
                    f'{func.__name__} {extra_info}took {value:.{self.precision}f} [{unit}]{iter_info}'
                )
                return result

            return wrapper

        return decorator

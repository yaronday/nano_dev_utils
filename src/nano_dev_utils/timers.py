from functools import wraps
import time
import logging
import inspect

from typing import (
    TypeVar,
    ParamSpec,
    Callable,
    Awaitable,
    Any,
    cast,
)

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

    def update(self, attrs: dict[str, Any]) -> None:
        update(self, attrs)

    def timeit(
        self,
        iterations: int = 1,
        timeout: float | None = None,
        per_iteration: bool = False,
    ) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
        """ Decorator that measures execution time for sync / async functions.

        Args:
            iterations: Number of times to run the function (averaged for reporting).
            timeout: Optional max allowed time (in seconds); raises TimeoutError if exceeded.
            per_iteration: If True, enforces timeout per iteration, else cumulatively.

        Returns:
        A decorated function that behaves identically to the original, with timing logged.
        """

        RP = ParamSpec('RP')
        RR = TypeVar('RR')

        def decorator(
            func: Callable[RP, RR] | Callable[RP, Awaitable[RR]],
        ) -> Callable[RP, Any]:
            if inspect.iscoroutinefunction(func):
                async_func = cast(Callable[RP, Awaitable[RR]], func)

                @wraps(func)
                async def async_wrapper(*args: RP.args, **kwargs: RP.kwargs) -> RR:
                    func_name = func.__name__
                    total_elapsed_ns = 0
                    result: RR | None = None
                    for i in range(1, iterations + 1):
                        start_ns = time.perf_counter_ns()
                        result = await async_func(*args, **kwargs)
                        duration_ns = time.perf_counter_ns() - start_ns
                        total_elapsed_ns += duration_ns

                        self._check_timeout(
                            func_name,
                            i,
                            duration_ns,
                            total_elapsed_ns,
                            timeout,
                            per_iteration,
                        )
                    avg_elapsed_ns = total_elapsed_ns / iterations
                    value, unit = self._to_units(avg_elapsed_ns)
                    msg = self._formatted_msg(
                        func_name, args, kwargs, value, unit, iterations
                    )
                    lgr.info(msg)
                    return cast(RR, result)

                return cast(Callable[RP, Awaitable[RR]], async_wrapper)
            else:
                sync_func = cast(Callable[RP, RR], func)

                @wraps(func)
                def sync_wrapper(*args: RP.args, **kwargs: RP.kwargs) -> RR:
                    func_name = func.__name__
                    total_elapsed_ns = 0
                    result: RR | None = None
                    for i in range(1, iterations + 1):
                        start_ns = time.perf_counter_ns()
                        result = sync_func(*args, **kwargs)
                        duration_ns = time.perf_counter_ns() - start_ns
                        total_elapsed_ns += duration_ns
                        self._check_timeout(
                            func_name,
                            i,
                            duration_ns,
                            total_elapsed_ns,
                            timeout,
                            per_iteration,
                        )
                    avg_elapsed_ns = total_elapsed_ns / iterations
                    value, unit = self._to_units(avg_elapsed_ns)
                    msg = self._formatted_msg(
                        func_name, args, kwargs, value, unit, iterations
                    )
                    lgr.info(msg)
                    return cast(RR, result)

                return cast(Callable[RP, RR], sync_wrapper)

        return decorator

    def _check_timeout(
        self,
        func_name: str,
        i: int,
        duration_ns: float,
        total_elapsed_ns: float,
        timeout: float | None,
        per_iteration: bool,
    ) -> None:
        """Raise TimeoutError if timeout is exceeded."""
        if timeout is None:
            return
        timeout_exceeded = f'{func_name} exceeded {timeout:.{self.precision}f}s'
        if per_iteration:
            duration_s = duration_ns / 1e9
            if duration_s > timeout:
                raise TimeoutError(
                    f'{timeout_exceeded} on iteration {i} '
                    f'(took {duration_s:.{self.precision}f}s)'
                )
        else:
            total_duration_s = total_elapsed_ns / 1e9
            if total_duration_s > timeout:
                raise TimeoutError(
                    f'{timeout_exceeded} after {i} iterations '
                    f'(took {total_duration_s:.{self.precision}f}s)'
                )

    def _to_units(self, avg_elapsed_ns: float) -> tuple[float, str]:
        """Convert nanoseconds to the appropriate time unit."""
        return next(
            (avg_elapsed_ns / div, u)
            for div, u in self.units
            if avg_elapsed_ns >= div or u == 'ns'
        )

    def _formatted_msg(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
        value: float,
        unit: str,
        iterations: int,
    ) -> str:
        extra_info = f'{args} {kwargs} ' if self.verbose else ''
        iter_info = f' (avg. over {iterations} runs)' if iterations > 1 else ''
        return f'{func_name} {extra_info}took {value:.{self.precision}f} [{unit}]{iter_info}'

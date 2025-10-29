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
        """Decorator that measures execution time for sync / async functions.

        Args:
            iterations: Number of times to run the function (averaged for reporting).
            timeout: Optional max allowed time (in seconds); raises TimeoutError if exceeded.
            per_iteration: If True, enforces timeout per iteration, else cumulatively.

        Returns:
        A decorated function that behaves identically to the original, with timing logged.
        """

        RP = ParamSpec('RP')
        RR = TypeVar('RR')

        precision = self.precision

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
                    duration_str = self._duration_formatter(avg_elapsed_ns, precision)
                    msg = self._formatted_msg(
                        func_name, args, kwargs, duration_str, iterations
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
                    duration_str = self._duration_formatter(avg_elapsed_ns, precision)
                    msg = self._formatted_msg(
                        func_name, args, kwargs, duration_str, iterations
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
        precision = self.precision
        timeout_exceeded = f'{func_name} exceeded {timeout:.{precision}f}s'
        if per_iteration:
            duration_s = duration_ns / 1e9
            if duration_s > timeout:
                raise TimeoutError(
                    f'{timeout_exceeded} on iteration {i} '
                    f'(took {duration_s:.{precision}f}s)'
                )
        else:
            total_duration_s = total_elapsed_ns / 1e9
            if total_duration_s > timeout:
                raise TimeoutError(
                    f'{timeout_exceeded} after {i} iterations '
                    f'(took {total_duration_s:.{precision}f}s)'
                )

    @staticmethod
    def _duration_formatter(elapsed_ns: float, precision: int = 4) -> str:
        """Convert nanoseconds to the appropriate time unit, supporting multi-unit results."""
        ns_sec, ns_min, ns_hour = 1e9, 6e10, 3.6e12
        ns_ms, ns_us = 1e6, 1e3

        if elapsed_ns < ns_sec:
            if elapsed_ns >= ns_ms:
                return f'{elapsed_ns / ns_ms:.{precision}f} [ms]'
            elif elapsed_ns >= ns_us:
                return f'{elapsed_ns / ns_us:.{precision}f} [μs]'
            return f'{elapsed_ns:.2f} [ns]'

        if elapsed_ns < ns_min:
            seconds = elapsed_ns / ns_sec
            return f'{seconds:.1f}s' if seconds < 10 else f'{seconds:.0f} [s]'

        if elapsed_ns >= ns_hour:
            hours = int(elapsed_ns / ns_hour)
            rem = elapsed_ns % ns_hour
            mins = int(rem / ns_min)
            secs = int((rem % ns_min) / ns_sec)

            parts = [f'{hours} [h]']
            if mins:
                parts.append(f'{mins} [m]')
            if secs:
                parts.append(f'{secs} [s]')
            return ' '.join(parts)

        else:
            minutes = int(elapsed_ns / ns_min)
            seconds = int((elapsed_ns % ns_min) / ns_sec)
            return f'{minutes} [m] {seconds} [s]' if seconds else f'{minutes} [m]'

    def _formatted_msg(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
        duration_str: str,
        iterations: int,
    ) -> str:
        extra_info = f'{args} {kwargs} ' if self.verbose else ''
        iter_info = f' (avg. over {iterations} runs)' if iterations > 1 else ''
        return f'{func_name} {extra_info}took {duration_str}{iter_info}'

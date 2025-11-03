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

NS_IN_US = 1_000
NS_IN_MS = 1_000_000
NS_IN_SEC = 1_000_000_000
NS_IN_MIN = 60 * NS_IN_SEC
NS_IN_HOUR = 60 * NS_IN_MIN


class Timer:
    def __init__(
        self, precision: int = 4, verbose: bool = False, printout: bool = False
    ):
        self.precision = precision
        self.verbose = verbose
        self.printout = printout

    def init(self, *args, **kwargs) -> None:
        self.__init__(*args, **kwargs)

    def update(self, attrs: dict[str, Any]) -> None:
        update(self, attrs)

    def res_formatter(self, elapsed_ns: float, *, precision: int = 4) -> str:
        return self._duration_formatter(elapsed_ns, precision=precision)

    def timeit(
        self,
        iterations: int = 1,
        timeout: float | None = None,
        per_iteration: bool = False,
    ) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
        """Decorator that measures execution time for sync / async functions.

        Args:
            iterations: int:  Number of times to run the function (averaged for reporting).
            timeout: float:   Optional max allowed time (in seconds); raises TimeoutError if exceeded.
            per_iteration: bool: If True, enforces timeout per iteration, else cumulatively.

        Returns:
        A decorated function that behaves identically to the original, with timing logged.
        """

        RP = ParamSpec('RP')
        RR = TypeVar('RR')

        precision, verbose, printout = self.precision, self.verbose, self.printout
        check_timeout = self._check_timeout
        duration_formatter = self._duration_formatter
        format_timing_msg = self._format_timing_msg

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

                        check_timeout(
                            func_name,
                            i,
                            duration_ns,
                            total_elapsed_ns,
                            timeout,
                            per_iteration,
                            precision,
                        )
                    avg_elapsed_ns = total_elapsed_ns / iterations
                    duration_str = duration_formatter(avg_elapsed_ns, precision)

                    msg = format_timing_msg(
                        func_name, args, kwargs, duration_str, iterations, verbose
                    )
                    lgr.info(msg)
                    if printout:
                        print(msg)
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
                        check_timeout(
                            func_name,
                            i,
                            duration_ns,
                            total_elapsed_ns,
                            timeout,
                            per_iteration,
                            precision,
                        )
                    avg_elapsed_ns = total_elapsed_ns / iterations
                    duration_str = duration_formatter(avg_elapsed_ns, precision)
                    msg = format_timing_msg(
                        func_name, args, kwargs, duration_str, iterations, verbose
                    )
                    lgr.info(msg)
                    if printout:
                        print(msg)
                    return cast(RR, result)

                return cast(Callable[RP, RR], sync_wrapper)

        return decorator

    @staticmethod
    def _check_timeout(
        func_name: str,
        i: int,
        duration_ns: float,
        total_elapsed_ns: float,
        timeout: float | None,
        per_iteration: bool,
        precision,
    ) -> None:
        """Raise TimeoutError if timeout is exceeded."""
        if timeout is None:
            return

        timeout_exceeded = f'{func_name} exceeded {timeout:.{precision}f} s'
        if per_iteration:
            duration_s = duration_ns / NS_IN_SEC
            if duration_s > timeout:
                raise TimeoutError(
                    f'{timeout_exceeded} on iteration {i} '
                    f'(took {duration_s:.{precision}f} s)'
                )
        else:
            total_duration_s = total_elapsed_ns / NS_IN_SEC
            if total_duration_s > timeout:
                raise TimeoutError(
                    f'{timeout_exceeded} after {i} iterations '
                    f'(took {total_duration_s:.{precision}f} s)'
                )

    @staticmethod
    def _duration_formatter(elapsed_ns: float, precision: int = 4) -> str:
        """Format a duration [ns] into the most appropriate time unit.

        Converts ns into a human-readable string with adaptive precision.
        Handles ns, μs, ms, s, m, and h, combining units where meaningful.
        """
        if elapsed_ns < NS_IN_SEC:
            if elapsed_ns >= NS_IN_MS:
                return f'{elapsed_ns / NS_IN_MS:.{precision}f} ms'
            if elapsed_ns >= NS_IN_US:
                return f'{elapsed_ns / NS_IN_US:.{precision}f} μs'
            return f'{elapsed_ns:.{precision}f} ns'

        if elapsed_ns < NS_IN_MIN:
            return f'{elapsed_ns / NS_IN_SEC:.{precision}f} s'

        if elapsed_ns >= NS_IN_HOUR:
            hours, rem = divmod(elapsed_ns, NS_IN_HOUR)
            mins, rem = divmod(rem, NS_IN_MIN)
            secs = rem // NS_IN_SEC

            parts = [f'{int(hours)} h']
            if mins:
                parts.append(f'{int(mins)} m')
            if secs:
                parts.append(f'{int(secs)} s')
            return ' '.join(parts)

        mins, rem = divmod(elapsed_ns, NS_IN_MIN)
        secs = rem // NS_IN_SEC
        return f'{int(mins)} m {int(secs)} s' if secs else f'{int(mins)} m'

    @staticmethod
    def _format_timing_msg(
        func_name: str,
        args: tuple,
        kwargs: dict,
        duration_str: str,
        iterations: int,
        verbose: bool,
    ) -> str:
        """Formats a concise timing message for a decorated function call.

        Args:
            func_name (str): Name of the function being measured.
            args (tuple): Positional arguments passed to the function.
            kwargs (dict): Keyword arguments passed to the function.
            duration_str (str): Formatted duration string (already unit-scaled).
            iterations (int): Number of timing iterations used for averaging.
            verbose (bool): Whether to include function arguments in the message.

        Returns:
            str: A formatted summary string, for example:
                'process_data took 12.31 ms (avg. over 10 runs)'
        """

        extra_info = f'{args!r} {kwargs!r} ' if verbose else ''
        iter_info = f' (avg. over {iterations} runs)' if iterations > 1 else ''
        return f'{func_name} {extra_info}took {duration_str}{iter_info}'

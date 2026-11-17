#!/usr/bin/env python3
"""Retry with exponential backoff, jitter, and an honest stop condition.

Most retry helpers make one of three mistakes: they retry errors that will never
succeed (a 400), they retry without limit, or they retry every task at the same
moment so a rate-limited service gets a synchronized second wave. This one retries
only what you name, caps the delay, and spreads the retries out.

Usage
-----
    from importlib import import_module
    backoff = import_module("04_retry_backoff")  # or copy the function into your project

    @backoff.retry(times=5, base=0.5, cap=16, retry_on=(TimeoutError, ConnectionError))
    def fetch(url):
        ...

    @backoff.retry(times=3, give_up_on=(ValueError, PermissionError))
    def parse(payload):
        ...

    # See it work:
    python3 04_retry_backoff.py --demo
"""

from __future__ import annotations

import argparse
import functools
import random
import sys
import time
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


def compute_delay(
    attempt: int,
    base: float,
    factor: float,
    cap: float,
    jitter: float,
    rand: Callable[[], float] = random.random,
) -> float:
    """Delay before retry number `attempt` (0-based), with symmetric jitter.

    Capped before jitter so the result never exceeds `cap * (1 + jitter)`.
    """
    raw = min(cap, base * (factor ** attempt))
    if jitter <= 0:
        return raw
    return raw * (1 + jitter * (2 * rand() - 1))


def retry(
    times: int = 4,
    base: float = 0.5,
    factor: float = 2.0,
    cap: float = 30.0,
    jitter: float = 0.25,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    give_up_on: tuple[type[BaseException], ...] = (),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rand: Callable[[], float] = random.random,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory.

    times     total attempts, including the first (times=1 means no retry)
    base      first delay in seconds
    factor    multiplier per attempt
    cap       maximum delay before jitter, in seconds
    jitter    fraction of the delay to randomise, 0 to disable
    retry_on  exception types that are retried
    give_up_on exception types that abort immediately, even if also in retry_on
    on_retry  callback(attempt, exception, delay) for logging
    sleep     injected for tests
    """
    if times < 1:
        raise ValueError("times must be at least 1")
    if base < 0 or cap < 0:
        raise ValueError("base and cap must not be negative")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last: BaseException | None = None
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except give_up_on:
                    raise
                except retry_on as exc:
                    last = exc
                    if attempt == times - 1:
                        break
                    delay = compute_delay(attempt, base, factor, cap, jitter, rand)
                    if on_retry is not None:
                        on_retry(attempt + 1, exc, delay)
                    sleep(delay)
            assert last is not None
            raise last

        return wrapper

    return decorator


def retry_sync(
    func: Callable[[], T],
    times: int = 4,
    base: float = 0.5,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    **kwargs,
) -> T:
    """The same behaviour without the decorator syntax."""
    return retry(times=times, base=base, retry_on=retry_on, **kwargs)(func)()


# --------------------------------------------------------------------------- demo

def _demo() -> int:
    calls = {"n": 0}

    @retry(times=4, base=0.05, cap=0.2, retry_on=(TimeoutError,),
           on_retry=lambda attempt, exc, delay: print(
               f"  retry {attempt} after {exc} in {delay:.3f}s"))
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError(f"attempt {calls['n']} timed out")
        return "ok"

    print("flaky():", flaky(), f"after {calls['n']} calls")

    @retry(times=3, base=0.01, retry_on=(Exception,), give_up_on=(ValueError,))
    def wrong() -> None:
        raise ValueError("this will never succeed")

    try:
        wrong()
    except ValueError as exc:
        print(f"wrong(): gave up immediately as intended ({exc})")

    print("\ndelay schedule (base=0.5, factor=2, cap=16, no jitter):")
    for attempt in range(7):
        print(f"  attempt {attempt + 1}: {compute_delay(attempt, 0.5, 2.0, 16.0, 0.0):6.2f}s")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exponential backoff with jitter.")
    parser.add_argument("--demo", action="store_true", help="run the built-in example")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 0
    try:
        return _demo()
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

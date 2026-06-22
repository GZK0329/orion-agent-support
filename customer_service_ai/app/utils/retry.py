from functools import wraps
from typing import Callable, TypeVar

from loguru import logger
from tenacity import (
    RetryError,
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT = 1
DEFAULT_MAX_WAIT = 10

RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

def with_retry(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: int = DEFAULT_MIN_WAIT,
    max_wait: int = DEFAULT_MAX_WAIT,
    operation_name: str = "operation",
) -> Callable:
    decorated = retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
    )

    def wrapper(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def inner(*args, **kwargs) -> T:
            try:
                return decorated(func)(*args, **kwargs)
            except RetryError:
                logger.error(f"{operation_name} 重试 {max_attempts} 次后仍然失败")
                raise

        return inner

    return wrapper

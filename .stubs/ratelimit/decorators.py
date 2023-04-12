from typing import Callable, ParamSpec, TypeVar

P = ParamSpec('P')
T = TypeVar('T')


class RateLimitDecorator:
    def __init__(self,
                 calls: int = ...,
                 period: float = ...,
                 clock: float = ...,
                 raise_on_limit: bool = ...) -> None:
        ...

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        ...


def sleep_and_retry(func: Callable[P, T]) -> Callable[P, T]:
    ...

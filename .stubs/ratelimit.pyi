from typing import Any, Callable


class RateLimitDecorator:
    def __init__(self,
                 calls: int = ...,
                 period: float = ...,
                 clock: float = ...,
                 raise_on_limit: bool = ...) -> None:
        ...

    def __call__(self, func: Any) -> Callable[..., Any]:
        ...


limits = RateLimitDecorator


def sleep_and_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    ...

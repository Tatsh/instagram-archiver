from typing import Any, Callable, Type


class RateLimiter:
    def __init__(self,
                 *,
                 max_calls: int,
                 period: int,
                 callback: Callable[[int], None] = ...) -> None:
        ...

    def __enter__(self) -> 'RateLimiter':
        ...

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException,
                 exc_tb: Any) -> None:
        ...

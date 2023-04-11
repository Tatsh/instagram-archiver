from typing import Callable, ParamSpec, TypeVar

P = ParamSpec('P')
RT = TypeVar('RT')


class HookimplMarker:
    def __call__(
        self,
        *,
        tryfirst: bool = ...,
    ) -> Callable[[Callable[P, RT]], Callable[P, RT]]:
        ...

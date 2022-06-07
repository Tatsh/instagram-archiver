from typing import (Any, Callable, Dict, Mapping, Optional, Sequence, Type,
                    Union)


def float_or_none(s: Optional[Union[str, int, float]]) -> Optional[float]:
    ...


def int_or_none(s: Optional[Union[str, int, float]]) -> Optional[int]:
    ...


def lowercase_escape(s: str) -> str:
    ...


def str_to_int(s: Optional[str]) -> Optional[int]:
    ...


def format_field(s: Optional[str], template: str) -> str:
    ...


def traverse_obj(obj: Mapping[str, Any],
                 *paths: Sequence[Any],
                 expected_type: Union[Type[str], Type[Dict[str, Any]],
                                      Callable[[Any], Any]] = ...,
                 fatal: Optional[bool] = ...) -> Any:
    ...

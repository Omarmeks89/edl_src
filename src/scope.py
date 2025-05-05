import copy
from typing import Any, Optional

from src.exceptions import TranslatorRuntimeError


class DynamicSymbolScope:
    """scope for collect symbols at runtime"""

    def __repr__(self) -> str:
        return f"{type(self).__name__}({[(k, v) for k, v in self.__dict__.items()]})"

    def set_symbol(self, key: str, value: Any) -> None:
        if not getattr(self, key, None):
            setattr(self, key, value)

    def update_symbol(self, key: str, value: Any) -> None:
        if getattr(self, key, None) is None:
            raise TranslatorRuntimeError(f"no key '{key}' in dynamic scope")
        setattr(self, key, value)

    def add_symbol(self, key: str, value: Any) -> None:
        item = getattr(self, key, None)
        if item is None or not isinstance(item, list):
            raise TranslatorRuntimeError(f"invalid key '{key}' to add")
        item.append(value)

    def isset(self, key: str) -> bool:
        return key in self.__dict__

    def remove_symbol(self, key: str) -> None:
        delattr(self, key)

    def get_symbol_value(self, key: str) -> Optional[Any]:
        return getattr(self, key, None)

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.__dict__)

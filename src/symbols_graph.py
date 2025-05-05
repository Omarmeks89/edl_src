"""Motivation: we have to be sure where and how we use marco symbols
to avoid undefined behaviour, so graph is responsible to help us"""

import weakref
from typing import Any, Optional

from .exceptions import TranslatorError


class orgnode:
    """macro symbols graph node
    (strong orgraph)"""

    @classmethod
    def create(cls, name: str, value: Any) -> "orgnode":
        """Create root node"""
        return orgnode(name, value=value)

    def __init__(
        self,
        name: str,
        *,
        value: Any | None = None,
        parent_node: Optional["orgnode"] = None,
    ) -> None:
        self.name = name
        self.value = value
        self.parent = None
        if parent_node is not None:
            self.parent = weakref.ref(parent_node)
        self.childs: list["orgnode"] = []

    def __repr__(self) -> str:
        p = None
        if self.parent is not None:
            p = self.parent()
        parent_name = p.name if p is not None else "-"
        return f"{type(self).__name__}(parent={parent_name}, name={self.name}, value={self.value}, childs={self.childs})"

    def add(self, node_name: str, value: Any) -> weakref.ref["orgnode"]:
        if self.name == node_name:
            return weakref.ref(self)

        for child in self.childs:
            if child.name == node_name:
                raise TranslatorError(f"node '{node_name}' registered")

        child_node = orgnode(node_name, value=value, parent_node=self)
        self.childs.append(child_node)
        return weakref.ref(child_node)

    def get_root_value(self) -> Any | None:
        """Lookup from leafs to root"""
        if self.parent is None:
            # the root
            return self.value

        parent = self.parent()
        if parent is None:
            raise TranslatorError(f"removed parent node for '{self.name}'")

        return parent.get_root_value()

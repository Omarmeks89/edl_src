"""Module contains data struct for resolve macro symbols O(n) runtime"""
from typing import Any

from src.exceptions import PreprocessorError


class ndef:
    """Is used as dummy value"""

    def __repr__(self) -> str:
        return "ndef"


class _streeNode:

    def __init__(self, sym: str) -> None:
        self.symbol: str = sym
        self.value: Any | None = None
        self.next: dict[str, _streeNode] = {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(s={self.symbol}, v={self.value}, next={self.next})"

    def __contains__(self, item: str) -> bool:
        return item in self.next


class stree:

    def __init__(self) -> None:
        self.roots: dict[str, _streeNode] = {}
        self.tmp: _streeNode | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(nodes={self.roots})"

    def add(self, sym: str, val: Any) -> None:
        """Add whole symbol and store value in leaf node.
        None value is not allowed

        Args:
            sym (str): full symbol name
            val (Any): any value to store
        """
        if val is None:
            raise PreprocessorError("None value not allowed for stree")

        nodes, snode = self.roots, None | _streeNode
        for s in sym:

            if s in nodes:
                nodes, snode = nodes[s].next, nodes[s]
                continue

            # add new symbol to chain
            snode = _streeNode(s)
            nodes[s] = snode
            nodes = snode.next

        # anyway we got snode not None
        if snode.value is not None:
            # attempt to redefine registered symbol
            raise PreprocessorError(
                    f"attempt to redefine existing symbol '{sym}'"
            )

        snode.value = val
        return None

    def find(self, sym: str) -> Any | None:
        """Try to find stored value by full symbol name

        Args:
            sym (str): full symbol name

        Returns:
            Any: - any stored value or None if symbol not exists
        """
        nodes, snode = self.roots, _streeNode("")
        for s in sym:
            if s in nodes:
                nodes, snode = nodes[s].next, nodes[s]

        return snode.value

    def resolve(self, sym: str) -> Any | None:
        """Is working as a generator.
        If not None returns that means wished symbol
        was found in stree and stored value returned

        Args:
            sym (str): each symbol of wished symbol name

        Returns:
            Any: - any stored value or None if symbol not registered
        """
        nodes = self.roots
        if self.tmp is not None:
            nodes = self.tmp.next

        if sym not in nodes:
            # drop tmp node - we can`t find
            # wished symbol
            self.tmp = None
            return None

        self.tmp = nodes[sym]
        val = self.tmp.value

        if val is not None:
            # stored value was found we have to
            # drop tmp node to start from scratch
            # for the next symbol
            self.tmp = None

        return val

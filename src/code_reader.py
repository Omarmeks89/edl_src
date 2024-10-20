import pathlib
from typing import Generator

from src.exceptions import TranslatorError


class CodeReader:
    """reader used for read and store read (as buffer) for postprocessor"""

    def __init__(self, f_name: str) -> None:
        self._f_name = f_name
        if not pathlib.Path(self._f_name).exists():
            raise TranslatorError(f"path {pathlib.Path(self._f_name)} not exists")

        self._lines: list[str] = []

    def __repr__(self) -> str:
        return f"{type(self).__name__}(file={self._f_name})"

    @property
    def name(self) -> str:
        return self._f_name

    def reader(self) -> Generator[None, None, str]:
        with open(self._f_name, "r", encoding="utf-8") as file:
            for line in file.readlines():
                self._lines.append(line)
                yield line

    def code_lines(self) -> Generator[tuple[int, str], None, None]:
        if len(self._lines) == 0:
            raise TranslatorError("no code lines found")

        for idx, line in enumerate(self._lines):
            yield idx, line

    def read_preprocessed(self) -> Generator[None, None, str]:
        """get preprocessed text to parser from memory"""
        if len(self._lines) == 0:
            raise TranslatorError("no code lines found")

        for line in self._lines:
            if line != "":
                yield line

    def replace(self, pos: int, line: str) -> None:
        if pos >= len(self._lines):
            raise TranslatorError(f"code line <{line}> out of range")

        self._lines[pos] = line

    def dump(self, fullpath: str) -> None:
        """dump preprocessing result"""
        with open(fullpath, "w", encoding="utf-8") as file:
            file.writelines(self._lines)

    def clear(self) -> None:
        self._lines.clear()
        self._f_name = ""

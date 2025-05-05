from typing import Generator

from src.exceptions import TranslatorError


class CodeReader:
    """reader used for read and store read (as buffer) for postprocessor"""

    def __init__(self, f_name: str) -> None:
        self._f_name = f_name
        self._lines: list[str] = []
        self._cache: list[str] = []

    def __repr__(self) -> str:
        return f"{type(self).__name__}(file={self._f_name}, lines={self._lines})"

    @property
    def name(self) -> str:
        return self._f_name

    @property
    def code(self) -> list[str]:
        return self._lines

    def reader(
        self,
        *,
        mode: str = "r",
        encoding: str = "utf-8",
    ) -> Generator[str, None, None]:
        if len(self._cache) == 0:
            with open(self._f_name, mode=mode, encoding=encoding) as file:
                for line in file.readlines():
                    yield line

        else:
            for line in self._cache:
                yield line

    def write_line(self, line: str) -> None:
        self._lines.append(line)

    def set_cache(self, lines: list[str]) -> None:
        self._cache = lines

    def code_lines(self) -> Generator[tuple[int, str], None, None]:
        if len(self._lines) == 0:
            raise TranslatorError("no code lines found")

        for idx, line in enumerate(self._lines):
            yield idx, line

    def get_code_line(self, idx: int) -> str:
        """
        Raises:
            IndexError: on invalid index
        """
        return self._lines[idx]

    def read_preprocessed(self) -> Generator[str, None, None]:
        """get preprocessed text to parser from memory"""
        if len(self._lines) == 0:
            raise TranslatorError("no code lines found")

        for line in self._lines:
            if line != "":
                yield line

    def replace(self, pos: int, line: str) -> None:
        if pos >= len(self._lines):
            raise TranslatorError(f"code line <{line!r}> out of range\n")

        self._lines[pos] = line

    def dump(self, fullpath: str) -> None:
        """dump preprocessing result"""
        with open(fullpath, "w", encoding="utf-8") as file:
            file.writelines(self._lines)

    def clear(self) -> None:
        self._lines.clear()
        self._cache.clear()
        self._f_name = ""

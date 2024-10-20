"""text preprocessor will use whe you need
additionally format symbols or represent any
expression as a single symbol"""
from enum import Enum
from typing import Mapping, NoReturn, Any, Generator, Optional

from .code_reader import CodeReader
from .exceptions import PreprocessorError


class TokenType(str, Enum):
    START_MACRO: str = "START_MACRO"
    LOAD: str = "LOAD"
    PARAMETER: str = "PARAMETER"
    SYMBOL: str = "SYMBOL"
    EMPTY: str = "EMPTY"
    EOL: str = "EOL"
    EOF: str = "EOF"


class PreprocessorToken:

    def __init__(self, value: str, _type: TokenType) -> None:
        self._value = value
        self._type = _type

    def __repr__(self) -> str:
        return f"{type(self).__name__}(val={self._value}, type={self._type})"

    @property
    def token_type(self) -> TokenType:
        return self._type

    @property
    def value(self) -> str:
        return self._value


class Lexer:
    """Lexer for preprocessor"""

    _reserved_keywords: Mapping[str, PreprocessorToken] = {
        "загрузить": PreprocessorToken("загрузить", TokenType.LOAD),
    }

    def __init__(self) -> None:
        self._reader: Optional[Generator[None, None, str]] = None
        self._code = ""
        self._pos = 0
        self._line_pos = 0

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def set_reader(self, reader: CodeReader) -> None:
        self._reader = reader.reader()

    def get_trace(self) -> str:
        if self._code == "":
            return "no trace"

        symbols = ["-" for _ in range(self._pos)]
        symbols.append("^")
        code_ptr = "".join(symbols)
        code = self._code
        return (
            f"{code[:-1]}\n{code_ptr}\n(pos=<{self._pos}>, "
            f"symbol=<{self._code[self._pos]!r}>, "
            f"line=<{self._line_pos}>)"
        )

    def _set_new_line(self):
        self._code: str = next(self._reader)
        if self._pos != 0:
            self._pos = 0
        self._line_pos += 1

    def _skip(self, to: str) -> None:
        """inside a comment we may have string like './path' so we
        should handle (skip) all kind or parentheses to.
        """
        self._pos += 1
        while self._pos < len(self._code) and self._code[self._pos] != to:
            if self._code[self._pos] in ("'", '"'):
                self._skip(self._code[self._pos])
                continue

            elif self._code[self._pos] == "\n":
                self._set_new_line()
                continue

            self._pos += 1

        if self._pos >= len(self._code):
            return

        if self._code[self._pos] != to:
            # code may end
            self.error(msg=f"symbol <{to}> is not closed")
        self._pos += 1

    def get_next_token(self) -> Generator[None, None, PreprocessorToken]:
        if self._reader is None:
            self.error(msg="code reader not set")

        self._set_new_line()
        self._code: str

        while self._pos < len(self._code):

            if self._code[self._pos] == "#":
                self._pos += 1
                yield PreprocessorToken("START_MACRO", TokenType.START_MACRO)

                while self._pos < len(self._code):

                    if self._code[self._pos].isalpha():
                        yield self._parse_literal(self._code)

                    elif self._code[self._pos] in ("'", '"'):
                        yield self._parse_as_parameter(
                            self._code, self._code[self._pos]
                        )

                    elif self._code[self._pos] in (" ", "\t"):
                        self._pos += 1

                    elif self._code[self._pos] == "\n":
                        yield PreprocessorToken("EOL", TokenType.EOL)
                        self._set_new_line()
                        break

                    elif self._code[self._pos] == "/":
                        self._set_new_line()
                        break

            else:
                try:
                    self._set_new_line()
                except StopIteration:
                    break

        yield PreprocessorToken("EOF", TokenType.EOF)

    def _parse_literal(self, code: str) -> PreprocessorToken:
        """parse literal as DIRECTIVE (if found) or as SYMBOL"""

        symbols: list[str] = []
        while self._pos < len(code) and (
            code[self._pos].isalpha()
            or code[self._pos] == "_"
            or code[self._pos].isdigit()
        ):
            symbols.append(code[self._pos])
            self._pos += 1

        symbol = "".join(symbols)
        token = self._reserved_keywords.get(symbol)
        if token is None:
            return PreprocessorToken(symbol, TokenType.SYMBOL)
        return token

    def _parse_as_parameter(self, code: str, quote: str) -> PreprocessorToken:
        """parse parameter"""
        self._pos += 1
        p_symbols: list[str] = []
        while self._pos < len(code) and code[self._pos] != quote:
            p_symbols.append(code[self._pos])
            self._pos += 1
        self._pos += 1
        return PreprocessorToken("".join(p_symbols), TokenType.PARAMETER)

    def error(self, *, msg: str = "") -> NoReturn:
        raise PreprocessorError(msg)


"""========================= EBNF preprocessor grammar =======================    
    directive : start (load | ...) EOL
    load      : LOAD_W param symbol
    param     : 'PARAMETER' | "PARAMETER"
    symbol    : SYMBOL
    start     : "#"
    LOAD_W    : "загрузить"
    EOL       : "\n"
"""


class SymbolsScope:
    def __init__(self) -> None:
        self._globals: Mapping[str, Any] = {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(globals={self._globals})"

    def set(self, symbol: str, data: Any) -> None:
        if symbol in self._globals:
            self.error(msg=f"attempt redefine global symbol {symbol}")
        self._globals[symbol] = data

    def get(self, symbol: str) -> str | None:
        return self._globals.get(symbol)

    def error(self, *, msg: str = "") -> NoReturn:
        raise NameError(msg)


class Loader:

    def load(self, f_name: str) -> str:
        with open(f_name, "r") as file:
            return file.read()


class Preprocessor:
    """this implementation preprocessor joined with parser"""

    def __init__(self, lexer: Lexer, reader: CodeReader, loader: Loader) -> None:
        self._lexer = lexer
        self._reader = reader
        self._loader = loader
        self._lexer.set_reader(self._reader)
        self._token_gen = self._lexer.get_next_token()
        try:
            self._token = next(self._token_gen)
        except StopIteration:
            self.error(msg="unexpected end of code")
        self._scope = SymbolsScope()

    @property
    def reader(self) -> CodeReader:
        return self._reader

    def __repr__(self) -> str:
        return f"{type(self).__name__}(\n\tlexer={self._lexer};\n\ttoken={self._token};\n\tscope={self._scope};\n\tcode={self._reader})"

    def eat(self, token_type: TokenType) -> None:
        if self._token.token_type == token_type:
            self._token = next(self._token_gen)
            return
        self.error(msg=f"invalid syntax:\n{self._lexer.get_trace()}")

    def _skip_eol(self) -> PreprocessorToken:
        while self._token.token_type == TokenType.EOL:
            print(self._token)
            self.eat(TokenType.EOL)
        return self._token

    def error(self, *, msg: str = "") -> NoReturn:
        raise PreprocessorError(msg)

    def clear(self) -> None:
        """clear all preprocessed context"""
        self._scope = None

    def preprocess(self) -> SymbolsScope:
        self.directive()
        return self._scope

    def directive(self) -> None:
        """process directive"""
        # we may have some empty strings before directives
        # we should skip them
        _ = self._skip_eol()
        while self._token.token_type != TokenType.EOF:
            self.eat(TokenType.START_MACRO)
            if self._token.token_type == TokenType.LOAD:
                # other future directives same
                self.load()
                self.eat(TokenType.EOL)

    def load(self) -> PreprocessorToken:
        """process load directive"""
        self.eat(TokenType.LOAD)
        token = self.param()
        try:
            data = self._loader.load(token.value)
            token = self.symbol()
            self._scope.set(token.value, data)
        except (OSError, FileNotFoundError) as err:
            self.error(msg=f"included file not found: {err}")
        return self._token

    def param(self) -> PreprocessorToken:
        """process param"""
        token = self._token
        self.eat(TokenType.PARAMETER)
        return token

    def symbol(self) -> PreprocessorToken:
        """process symbol"""
        token = self._token
        self.eat(TokenType.SYMBOL)
        return token


class TextProcessor:
    """resume symbols into variables"""

    def __init__(self, preprocessor: Preprocessor) -> None:
        self._preproc = preprocessor
        self._code: str = ""
        self._pos = 0

    def __repr__(self) -> str:
        return f"{type(self).__name__}(\n\tpreprocessor={self._preproc};\n\tcode_line={self._code}\n)"

    def error(self, *, msg: str = "") -> NoReturn:
        raise PreprocessorError(msg)

    def get_trace(self) -> str:
        if self._code == "":
            return "no trace"
        symbols = ["-" for _ in range(self._pos)]
        symbols.append("^")
        code_ptr = "".join(symbols)
        code = self._code
        return f"\n{code[:-1]}\n{code_ptr}\n(pos=<{self._pos}>, symbol=<{self._code[self._pos]!r}>)"

    def process(self) -> None:
        symbols = self._preproc.preprocess()
        self._process(symbols)

    @staticmethod
    def _next_line(code: Generator[tuple[int, str], None, None]) -> tuple[int, str]:
        try:
            return next(code)
        except StopIteration:
            return -1, ""

    def _process(self, symbols: SymbolsScope) -> None:
        code = self._preproc.reader.code_lines()
        code_pos, self._code = self._next_line(code)

        while self._pos < len(self._code):
            if self._code[self._pos] == "#":
                self._preproc.reader.replace(code_pos, "")
                code_pos, self._code = self._next_line(code)
                self._pos = 0
                continue

            elif self._code[self._pos] == "$":
                # we have found var declaration
                data = self._substitute(self._code, symbols)
                if data != "":
                    self._preproc.reader.replace(code_pos, data)
                code_pos, self._code = self._next_line(code)
                self._pos = 0
                continue

            elif self._code[self._pos] in ("'", '"', "/"):
                self._skip(code, self._code[self._pos])
                code_pos, self._code = self._next_line(code)
                self._pos = 0
                continue

            elif (self._pos + 1) >= len(self._code):
                code_pos, self._code = self._next_line(code)
                self._pos = 0
                continue

            self._pos += 1

        self._pos = 0

    def _substitute(self, code: str, symbols: SymbolsScope) -> str:
        symb: list[str] = []
        self._pos += 1

        while self._pos < len(code):
            if code[self._pos] == "=":
                while self._pos < len(code):
                    if (
                        code[self._pos].isalpha()
                        or code[self._pos].isdigit()
                        or code[self._pos] == "_"
                    ):
                        symb.append(code[self._pos])

                    elif code[self._pos] == ";":
                        break

                    self._pos += 1

                symbol = "".join(symb)
                replacement = symbols.get(symbol)
                if replacement is None:
                    return ""

                code_line = replacement.replace("\n", "").strip()
                return code.replace(symbol, code_line)

            self._pos += 1

        # nothing was found
        return ""

    def _skip(self, code: Generator[tuple[int, str], None, None], to: str) -> None:
        self._pos += 1
        while self._pos < len(self._code) and self._code[self._pos] != to:
            if self._code[self._pos] in ("'", '"'):
                self._skip(code, self._code[self._pos])
                continue

            elif self._code[self._pos] == "\n":
                _, self._code = self._next_line(code)
                self._pos = 0
                continue

            self._pos += 1

        if self._pos >= len(self._code):
            return

        if self._code[self._pos] != to:
            # code may end
            self.error(msg=f"symbol <{to}> is not closed")

        self._pos += 1

    def dump(self, fullpath: str) -> None:
        self._preproc.reader.dump(fullpath)


def make_processor(code_reader: CodeReader) -> TextProcessor:
    """Preprocessor instance factory"""

    loader = Loader()
    lexer = Lexer()
    preproc = Preprocessor(lexer, code_reader, loader)
    return TextProcessor(preproc)

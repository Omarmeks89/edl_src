"""text preprocessor will use whe you need
additionally format symbols or represent any
expression as a single symbol"""

import pathlib
from enum import StrEnum
from typing import Mapping, NoReturn, Any, Generator, Optional

from .code_reader import CodeReader
from .exceptions import PreprocessorError


class TokenType(StrEnum):
    START_MACRO: str = "START_MACRO"
    UPLOAD: str = "UPLOAD"
    DEFINE: str = "DEFINE"
    PARAMETER: str = "PARAMETER"
    SYMBOL: str = "SYMBOL"
    VALUE: str = "VALUE"
    EMPTY: str = "EMPTY"
    EOL: str = "EOL"
    EOF: str = "EOF"


class PreprocessorToken:

    def __init__(
            self,
            value: str,
            _type: TokenType,
            token_len: int,
            *,
            code_line: int = 0,
            file_name: str = "",
    ) -> None:
        self.value = value
        self.type: TokenType = _type

        # extension for more reach trace
        self.token_len: int = token_len
        self.code_line_no: int = code_line
        self.file_name: str = file_name

    def __repr__(self) -> str:
        return f"{type(self).__name__}(val={self.value}, type={self.type})"


class Lexer:
    """Lexer for preprocessor"""

    _reserved_keywords: Mapping[str, PreprocessorToken] = {
            "upload": PreprocessorToken("upload", TokenType.UPLOAD, 9),
            "define": PreprocessorToken("define", TokenType.DEFINE, 6),
    }

    def __init__(self) -> None:
        self._reader_obj: CodeReader | None = None
        self._code_gen: Optional[Generator[str, None, None]] = None
        self._code = ""
        self._pos = 0  # pointer on symbol in code
        self._line_pos = 0  # pointer on line position

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def set_reader(self, reader: CodeReader) -> None:
        self._reader_obj = reader
        self._code_gen = reader.reader()

    def get_trace(self, token: PreprocessorToken) -> str:
        """
        moment of error ...
                  ^~~~~
        ----------|

        test.edl:10
        """
        # if line ended with EOL and symbol pointer on last position
        # we have to shift pointer left on 1 position
        if self._code[-1] == "\n" and self._pos == len(self._code):
            self._pos -= 1

        # trim tail whitespace or <LF> for
        # valid trace output
        code = self._code.strip()
        if code == "":
            self.error(msg="no code")

        # build error pointer (move ptr back to 1st token symbol)
        path = [" " for _ in range(self._pos - token.token_len)]
        path.append("^")
        for _ in range(token.token_len - 1):
            path.append("~")

        path.append("\n")

        # build underline
        for _ in range(self._pos - token.token_len):
            path.append("_")

        path.append(f"|({self._pos - token.token_len + 1})\n\n")
        path.append(f"{self._reader_obj.name}:{self._line_pos}")
        trace = "".join(path)

        return f"{code}\n{trace}\n"

    def _set_new_line(self) -> bool:
        try:
            self._code: str = next(self._code_gen)
        except StopIteration:
            # no more code - exit
            return False

        # update pointers for new line
        if self._pos != 0:
            self._pos = 0
        self._line_pos += 1

        return True

    def get_next_token(self) -> Generator[None, None, PreprocessorToken]:
        if self._code_gen is None:
            self.error(msg="code reader not set")

        self._set_new_line()
        self._code: str

        while self._pos < len(self._code):

            print(self._reader_obj)

            if self._code[self._pos] == "#":
                self._pos += 1
                yield PreprocessorToken(
                        "START_MACRO",
                        TokenType.START_MACRO,
                        1,
                        code_line=self._line_pos,
                        file_name=self._reader_obj.name,
                )

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
                        self._reader_obj.write_line(self._code)
                        yield PreprocessorToken(
                                "EOL",
                                TokenType.EOL,
                                1,
                                code_line=self._line_pos,
                                file_name=self._reader_obj.name,
                        )
                        self._set_new_line()
                        break

                    # skip comment
                    elif self._code[self._pos] == "/":
                        self._reader_obj.write_line(self._code)
                        self._set_new_line()
                        break

                    # digits (nums)
                    elif self._code[self._pos].isdigit():
                        yield self._parse_numeric(self._code)

                    # scip other symbols - we don`t see them

            else:
                self._reader_obj.write_line(self._code)
                if not self._set_new_line():
                    break

        print(self._reader_obj)
        yield PreprocessorToken(
                "EOF",
                TokenType.EOF,
                1,
                code_line=self._line_pos,
                file_name=self._reader_obj.name,
        )

    def _parse_numeric(self, code: str) -> PreprocessorToken:
        symbols: list[str] = []
        # '.' from locale
        while self._pos < len(code):
            if code[self._pos].isdigit() or code[self._pos] == ".":
                symbols.append(code[self._pos])
                self._pos += 1
                continue

            elif code[self._pos] == " " or code[self._pos] == "\n":
                self._pos += 1
                break

            # handle unexpected (for numeric value) symbol
            # build trace and raise error
            # add first unsupported symbol to trace
            symbols.append(code[self._pos])
            self._pos += 1
            numeric = "".join(symbols)
            t = PreprocessorToken(
                    numeric,
                    TokenType.VALUE,
                    len(numeric),
                    code_line=self._line_pos,
                    file_name=self._reader_obj.name,
            )
            self.error(msg=f"not numerical symbol\n{self.get_trace(t)}")

        numeric = "".join(symbols)
        return PreprocessorToken(
                numeric,
                TokenType.VALUE,
                len(numeric),
                code_line=self._line_pos,
                file_name=self._reader_obj.name,
        )

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

            # user defined symbol
            return PreprocessorToken(
                    symbol,
                    TokenType.SYMBOL,
                    len(symbol),
                    code_line=self._line_pos,
                    file_name=self._reader_obj.name,
            )

        return token

    def _parse_as_parameter(self, code: str, quote: str) -> PreprocessorToken:
        """parse parameter"""
        self._pos += 1
        p_symbols: list[str] = []

        while self._pos < len(code) and code[self._pos] != quote:
            p_symbols.append(code[self._pos])
            self._pos += 1
        self._pos += 1

        token_value = "".join(p_symbols)
        return PreprocessorToken(
                token_value,
                TokenType.PARAMETER,
                len(token_value),
                code_line=self._line_pos,
                file_name=self._reader_obj.name,
        )

    def error(self, *, msg: str = "") -> NoReturn:
        raise PreprocessorError(msg)


"""========================= EBNF preprocessor grammar =======================    
    directive       : START_MACRO (upload | define) EOL
    upload          : upload_kw parameter symbol
    upload_kw       : upload
    parameter       : [\"\'a-zA-Zа-яА-Я_0-9\/\\]+
    symbol          : [a-zA-Zа-яА-Я_0-9]+
    
    define          : define_kw symbol (value *)
    define_kw       : define
    symbol          : [a-zA-Zа-яА-Я_0-9]+
    value           : numerical | literal
    numerical       : [0-9a-fA-FOo\.]+
    literal         : [\"\'a-zA-Zа-яА-Я_0-9\/\\]+
    
    START_MACRO     : "#"
    EOL             : "\n"
"""


class Loader:
    """Loader used in 'upload' directive to load files"""

    def load(
            self,
            f_name: str,
            *,
            mode: str = "r",
            encoding: str = "utf-8"
    ) -> str:
        with open(f_name, mode=mode, encoding=encoding) as file:
            return file.read()


class init:
    """specific class for mark defined preprocessor symbols"""

    def __repr__(self) -> str:
        return "defined"


class Directive:

    def handle(self, visitor: Any) -> Any:
        return visitor.visit(self)


# =============================== Directives ===================================


class DefineDirective(Directive):

    def __init__(
            self,
            token: PreprocessorToken,
            code_line: str,
            *,
            value: Any | None = None
    ) -> None:
        self.token = token
        self.code = code_line
        self.value: Any | None = None


class UploadDirective(Directive):

    def __init__(
            self,
            token: PreprocessorToken,
            path: str | pathlib.Path,
            code_line: str
    ) -> None:
        self.token = token
        self.code = code_line
        self.path = path


class SymbolsScope(dict):

    def __setitem__(self, symbol: str, data: Any) -> None:
        s = super().get(symbol)
        if s is not None:
            self.error(msg=f"attempt redefine global symbol {symbol}")
        super().__setitem__(symbol, data)

    def error(self, *, msg: str = "") -> NoReturn:
        raise NameError(msg)


class Preprocessor:
    """this implementation preprocessor joined with parser"""

    def __init__(self, lexer: Lexer, reader: CodeReader) -> None:
        self._lexer = lexer
        self._reader = reader
        self._lexer.set_reader(self._reader)
        self._token_gen = self._lexer.get_next_token()
        try:
            self._token = next(self._token_gen)
        except StopIteration:
            self.error(msg="unexpected EOF")

        self._scope = SymbolsScope()

    @property
    def reader(self) -> CodeReader:
        return self._reader

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def eat(self, token_type: TokenType) -> None:
        if self._token.type == token_type:
            self._token = next(self._token_gen)
            return
        self.error(
                msg=f"unexpected symbol '{self._token.value}'\n"
                    f"{self._lexer.get_trace(self._token)}"
        )

    def _skip_eol(self) -> PreprocessorToken:
        while self._token.type == TokenType.EOL:
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

        while self._token.type != TokenType.EOF:

            self.eat(TokenType.START_MACRO)
            if self._token.type == TokenType.UPLOAD:
                self.upload()

            # other future directives same
            elif self._token.type == TokenType.DEFINE:
                self.define()

            else:
                self.error(
                        msg=f"unexpected symbol '{self._token.value}'\n"
                            f"{self._lexer.get_trace(self._token)}"
                )

            if self._token.type == TokenType.EOL:
                self.eat(TokenType.EOL)

    def upload(self) -> PreprocessorToken:
        """process load directive"""
        self.eat(TokenType.UPLOAD)
        token = self.param()
        symbol = self.symbol()
        self._scope[symbol.value] = token.value
        return self._token

    def define(self) -> PreprocessorToken:
        """define new preprocessor symbol"""

        self.eat(TokenType.DEFINE)
        symbol = self.symbol()

        if self._token.type == TokenType.VALUE:
            self._scope[symbol.value] = self.value().value

        elif self._token.type == TokenType.PARAMETER:
            self._scope[symbol.value] = self.param().value

        else:
            # means no value or parameter after define,
            # we define only symbol
            # do not eat, next token have to be EOL
            self._scope[symbol.value] = init()

        return self._token

    def _get_code_line(self, line_no: int) -> str:
        try:
            return self._reader.get_code_line(line_no)
        except IndexError:
            self.error(msg=f"line {line_no} not found\n")

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

    def value(self) -> PreprocessorToken:
        """process value"""
        token = self._token
        self.eat(TokenType.VALUE)
        return token


class NodeVisitor:

    def visit(self, node: Directive) -> Any:
        method = getattr(self, f"visit_{type(node).__name__}", self._error)
        return method(node)

    def _error(self, node: Directive) -> NoReturn:
        raise PreprocessorError(f"unexpected directive {type(node).__name__}")


class TextProcessor(NodeVisitor):
    """resume symbols into variables"""

    def __init__(self, preprocessor: Preprocessor, loader: Loader) -> None:
        self._preproc = preprocessor
        self._loader = loader
        self._code: str = ""
        self._pos = 0

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def error(self, *, msg: str = "") -> NoReturn:
        raise PreprocessorError(msg)

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
        print(self._preproc.reader)
        code = self._preproc.reader.code_lines()
        code_pos, self._code = self._next_line(code)

        while self._pos < len(self._code):
            if self._code[self._pos] == "#":
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
                    self.error(msg=f"symbol '{symbol}' not resolved")

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
    preproc = Preprocessor(lexer, code_reader)
    return TextProcessor(preproc, loader)

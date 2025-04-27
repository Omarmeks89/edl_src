"""text preprocessor will use whe you need
additionally format symbols or represent any
expression as a single symbol"""

import pathlib
from enum import StrEnum
from typing import Mapping, NoReturn, Any, Generator, Optional

from .code_reader import CodeReader
from .exceptions import PreprocessorError
from .stree import stree, ndef


class TokenType(StrEnum):
    START_MACRO: str = "START_MACRO"
    UPLOAD: str = "UPLOAD"
    DEFINE: str = "DEFINE"
    SYMBOL: str = "SYMBOL"
    LITERAL: str = "LITERAL"
    NUMERIC: str = "NUMERIC"
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
            "upload": PreprocessorToken("upload", TokenType.UPLOAD, 6),
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
                        yield self._parse_symbol(self._code)

                    elif self._code[self._pos] in ("'", '"'):
                        yield self._parse_as_literal(
                            self._code,
                            self._code[self._pos]
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

                    # trace on unsupported symbols (array, dict)
                    elif self._code[self._pos] == "{":
                        pos = self._code.find("}")
                        symb = self._code[self._pos]
                        trace_token = PreprocessorToken(
                            self._code[self._pos],
                            TokenType.SYMBOL,
                            pos - self._pos,
                            code_line=self._line_pos,
                            file_name=self._reader_obj.name,
                        )

                        # shift pos forward for valid trace message
                        self._pos = pos
                        self.error(
                                msg=f"unsupported macro symbol '{symb}'\n\n"
                            f"{self.get_trace(trace_token)}"
                        )

                    elif self._code[self._pos] == "[":
                        pos = self._code.find("]")
                        symb = self._code[self._pos]
                        trace_token = PreprocessorToken(
                            self._code[self._pos],
                            TokenType.SYMBOL,
                            pos - self._pos,
                            code_line=self._line_pos,
                            file_name=self._reader_obj.name,
                        )

                        # shift pos forward for valid trace message
                        self._pos = pos
                        self.error(
                                msg=f"unsupported macro symbol '{symb}'\n\n"
                            f"{self.get_trace(trace_token)}"
                        )

            else:
                self._reader_obj.write_line(self._code)
                if not self._set_new_line():
                    break

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
                # self._pos += 1
                break

            # handle unexpected (for numeric value) symbol
            # build trace and raise error
            # add first unsupported symbol to trace
            symbols.append(code[self._pos])
            self._pos += 1
            numeric = "".join(symbols)
            t = PreprocessorToken(
                numeric,
                    TokenType.NUMERIC,
                len(numeric),
                code_line=self._line_pos,
                file_name=self._reader_obj.name,
            )
            self.error(
                    msg=f"not numerical symbol " f"'{numeric[-1]}'\n\n{self.get_trace(t)}"
            )

        numeric = "".join(symbols)
        return PreprocessorToken(
            numeric,
                TokenType.NUMERIC,
            len(numeric),
            code_line=self._line_pos,
            file_name=self._reader_obj.name,
        )

    def _parse_symbol(self, code: str) -> PreprocessorToken:
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

    def _parse_as_literal(self, code: str, quote: str) -> PreprocessorToken:
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
                TokenType.LITERAL,
            len(token_value),
            code_line=self._line_pos,
            file_name=self._reader_obj.name,
        )

    def error(self, *, msg: str = "") -> NoReturn:
        raise PreprocessorError(msg)


"""========================= EBNF preprocessor grammar =======================    
    directive       : START_MACRO (upload | define) EOL
    upload          : upload_kw literal symbol
    upload_kw       : upload
    
    define          : define_kw symbol (numeric | literal)*
    define_kw       : define
    
    symbol          : [a-zA-Zа-яА-Я_0-9]+
    numeric         : [0-9a-fA-FOo\.]+
    literal         : [\"\'a-zA-Zа-яА-Я_0-9\/\\]+
    
    START_MACRO     : "#"
    EOL             : "\n"
"""


class Loader:
    """Loader used in 'upload' directive to load files"""

    def load(self, f_name: str, *, mode: str = "r", encoding: str = "utf-8") -> str:
        with open(f_name, mode=mode, encoding=encoding) as file:
            return file.read()


class Directive:

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"


# =============================== Directives ===================================


class DefineDirective(Directive):

    def __init__(
            self,
            token: PreprocessorToken,
            *,
            value: Any | None = None,
    ) -> None:
        self.token = token
        self.sym_name: str = token.value
        self.code_line_pos = token.code_line_no
        self.value: Any | None = value


class UploadDirective(Directive):

    def __init__(
            self,
            token: PreprocessorToken,
            path: str | pathlib.Path,
    ) -> None:
        self.token = token
        self.sym_name: str = token.value
        self.code_line_pos = token.code_line_no
        self.path = path


class Declaration:

    def __init__(self, sym_name: str, value: Any) -> None:
        self.name = sym_name
        self.value = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name}, value={self.value})"


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

        # create stree to store symbols
        self._scope: list[Directive] = []

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
                msg=f"unexpected symbol '{self._token.value}'\n\n"
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

    def preprocess(self) -> list[Directive]:
        """Provide all parsed directives for preprocessor"""
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
                        msg=f"unexpected symbol '{self._token.value}'\n\n"
                    f"{self._lexer.get_trace(self._token)}"
                )

            if self._token.type == TokenType.EOL:
                self.eat(TokenType.EOL)

    def upload(self) -> PreprocessorToken:
        """process load directive"""
        self.eat(TokenType.UPLOAD)
        token = self.literal()
        symbol = self.symbol()

        self._scope.append(UploadDirective(symbol, token.value))
        return self._token

    def define(self) -> PreprocessorToken:
        """define new preprocessor symbol"""

        value = None
        self.eat(TokenType.DEFINE)
        symbol = self.symbol()

        if self._token.type == TokenType.NUMERIC:
            value = self.numeric().value

        elif self._token.type == TokenType.LITERAL:
            # parameter means any string literal
            value = f'"{self.literal().value}"'

        self._scope.append(DefineDirective(symbol, value=value))
        return self._token

    def _get_code_line(self, line_no: int) -> str:
        try:
            return self._reader.get_code_line(line_no)
        except IndexError:
            self.error(msg=f"line {line_no} not found\n")

    def literal(self) -> PreprocessorToken:
        """process param"""
        token = self._token
        self.eat(TokenType.LITERAL)
        return token

    def symbol(self) -> PreprocessorToken:
        """process symbol"""
        token = self._token
        self.eat(TokenType.SYMBOL)
        return token

    def numeric(self) -> PreprocessorToken:
        """process value"""
        token = self._token
        self.eat(TokenType.NUMERIC)
        return token


class NodeVisitor:

    def visit(self, node: Directive) -> Any:
        method = getattr(self, f"visit_{type(node).__name__}", self._error)
        return method(node)

    def _error(self, node: Directive) -> NoReturn:
        raise PreprocessorError(f"unexpected directive {type(node).__name__}")


class TextProcessor(NodeVisitor):

    def __init__(
            self,
            preprocessor: Preprocessor,
            reader: CodeReader,
            loader: Loader,
            *,
            repr_only: bool = False,
    ) -> None:
        self._preproc = preprocessor
        self._loader = loader
        self._reader = reader

        # init symbols tree
        self._stree: stree = stree()

        # flags
        self._repr_only: bool = repr_only

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def error(self, *, msg: str = "") -> NoReturn:
        raise PreprocessorError(msg)

    def process(self) -> None:
        self.process_directives(self._preproc.preprocess())
        self.make_all_substitutions()

    @staticmethod
    def _next_line(code: Generator[tuple[int, str], None, None]) -> tuple[int, str]:
        try:
            return next(code)
        except StopIteration:
            return -1, ""

    def process_directives(self, directives: list[Directive]) -> None:
        for d in directives:
            self.visit(d)

    def make_all_substitutions(self) -> None:
        code = self._reader.code_lines()
        line_pos, code_line = self._next_line(code)
        pos = 0

        while line_pos >= 0:
            # if we got -1 from _next_line we will break loop

            # skip preproc directive (actual if repr_only is active)
            if code_line.startswith("#"):
                line_pos, code_line = self._next_line(code)
                pos = 0
                continue

            value: Declaration = self._stree.resolve(code_line[pos])
            if value is not None:

                # ndef value not allowed to use as substitution
                if isinstance(value.value, ndef):
                    self.error(
                            msg=f"symbol '{value.name}' have no value to substitute"
                    )

                self.substitute(line_pos, code_line, pos, value)

            pos += 1
            if pos >= len(code_line):
                line_pos, code_line = self._next_line(code)
                pos = 0

    def visit_UploadDirective(self, node: UploadDirective) -> None:
        """upload required data and set symbol with value into stree"""
        value = self._loader.load(node.path)
        self._stree.add(node.sym_name, Declaration(node.sym_name, value))
        self.replace_as_an_empty_line(node.code_line_pos - 1)

    def visit_DefineDirective(self, node: DefineDirective) -> None:
        """set defined symbol (with value) into stree"""
        v = node.value
        if v is None:
            v = ndef()
        self._stree.add(node.sym_name, Declaration(node.sym_name, v))
        self.replace_as_an_empty_line(node.code_line_pos - 1)

    def replace_as_an_empty_line(self, pos: int) -> None:
        """If repr_only flag is set as True, replacement
        will be skipped, else wished code line will be replaced
        on <LF> symbol"""
        if self._repr_only:
            return None

        self._reader.replace(pos, "\n")

    def substitute(
            self,
            line_idx: int,
            code: str,
            pos: int,
            d: Declaration
    ) -> None:
        to_pos = (pos + 1) - len(d.name)
        self._reader.replace(
            line_idx,
            self.replace_code_line(code[:to_pos], d.value)
            )

    @staticmethod
    def replace_code_line(code: str, update: str) -> str:
        return "".join([code, update, ";\n"])

    def dump(self, fullpath: str) -> None:
        self._reader.dump(fullpath)


def make_processor(code_reader: CodeReader) -> TextProcessor:
    """Preprocessor instance factory"""

    loader = Loader()
    lexer = Lexer()
    preproc = Preprocessor(lexer, code_reader)
    return TextProcessor(preproc, code_reader, loader)

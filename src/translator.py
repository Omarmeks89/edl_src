"""translator implementation"""

from typing import Mapping, Optional, Generator, NoReturn

from src.ast import (
    AstNode,
    Module,
    Object,
    Template,
    Context,
    Signal,
    SignalDirection,
    SignalType,
    ObjectType,
    UseDirective,
    UseMethod,
    UseVals,
    Value,
    Var,
    UseDirectiveFilter,
    UseDest,
    PutDirective,
    PutRule,
    PutIn,
    PutFrom,
    Connection,
    VarDeclaration,
    DynamicVarName,
    VarAssign,
    _T,
    ArrayValue,
    TildaValue,
    Range,
    Parameter,
    ParamDeclaration,
    ParameterAssign,
    SystemConstValue,
    ParameterOption,
    _ArrT,
    BindDirective,
)
from src.code_reader import CodeReader
from src.exceptions import TranslatorError
from src.tokens import TranslatorToken, Token

# recursion depth limit
TYPE_MATCHING_LIMIT: int = 100


class Tokenizer:
    """tokenizer (Lexer) for code interpreter.
    Some methods are same as Preprocessor Lexer (inheritance?)
    """

    _reserved_keywords: Mapping[str, Token] = {
            "оборудование": Token("оборудование", TranslatorToken.OBJ_CLASS),
            "класс_а":      Token("аналог", TranslatorToken.OBJ_TYPE),
            "класс_ц":      Token("цифра", TranslatorToken.OBJ_TYPE),
            "шаблон":       Token("шаблон", TranslatorToken.TEMPL_KW),
            "контекст":     Token("контекст", TranslatorToken.CTX_KW),
            "соединение":   Token("соединение", TranslatorToken.CONN_KW),
            "обработчик":   Token("обработчик", TranslatorToken.CONN_OPT),
            "сигнал":       Token("сигнал", TranslatorToken.SIGN_KW),
            # add sign opt
            "статус":       Token("статус", TranslatorToken.SIGN_OPT),
            "важность":     Token("важность", TranslatorToken.SIGN_OPT),
            "отображать":   Token("отображать", TranslatorToken.SIGN_OPT),
            "метка":        Token("метка", TranslatorToken.SIGN_OPT),
            "входной":      Token("входной", TranslatorToken.SIGN_DIRECT),
            "выходной":     Token("выходной", TranslatorToken.SIGN_DIRECT),
            "аналог":       Token("аналог", TranslatorToken.SIGN_TYPE),
            "дискрет":      Token("дискрет", TranslatorToken.SIGN_TYPE),
            "использовать": Token("использовать", TranslatorToken.USE_KW),
            "линейно":      Token("линейно", TranslatorToken.USE_METHOD),
            "значения":     Token("значения", TranslatorToken.VALS_KW),
            "кроме":        Token("кроме", TranslatorToken.EXCL_KV),
            "все":          Token("все", TranslatorToken.ALL),
            "подстановка":  Token("подстановка", TranslatorToken.PUT_KW),
            "правило":      Token("правило", TranslatorToken.RULE_KW),
            "в":            Token("в", TranslatorToken.IN),
            "из":           Token("из", TranslatorToken.FROM),
            "str":          Token("str", TranslatorToken.STR_CONST),
            "int":          Token("int", TranslatorToken.INT_CONST),
            "float":        Token("float", TranslatorToken.FLOAT_CONST),
            "bool":         Token("bool", TranslatorToken.BOOL_CONST),
            "arr":          Token("ARR", TranslatorToken.ARRAY_CONST),
            "Да":           Token("Да", TranslatorToken.BOOL),
            "Нет":          Token("Нет", TranslatorToken.BOOL),
            "диапазон":     Token("диапазон", TranslatorToken.RANGE_KW),
            "i":            Token("<i>", TranslatorToken.IT),
            "норма":        Token("норма", TranslatorToken.S_CONST),
            "авария":       Token("авария", TranslatorToken.S_CONST),
            "тревога":      Token("тревога", TranslatorToken.S_CONST),
            "привязать":    Token("привязать", TranslatorToken.BIND_KW),
            "параметр": Token("параметр", TranslatorToken.SIGN_OPT),
    }

    def __init__(self) -> None:
        self._reader: Optional[Generator[None, None, str]] = None
        self._code: str = ""
        self._pos: int = 0
        self._line_pos: int = 0

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self._code})"

    def set_reader(self, reader: CodeReader) -> None:
        self._reader = reader.read_preprocessed()

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
            self.error(msg=f"symbol <{to}> is not closed")
        self._pos += 1

    def get_next_token(self) -> Generator[None, None, Token]:
        if self._reader is None:
            self.error(msg="code reader not set")

        self._set_new_line()
        self._code: str

        while self._pos < len(self._code):
            if self._code[self._pos] == "$":
                self._pos += 1
                yield Token("$", TranslatorToken.VAR_SYMB)

            elif self._code[self._pos] in (" ", "\t"):
                self._pos += 1

            elif self._code[self._pos] == "~":
                self._pos += 1
                yield Token("~", TranslatorToken.TILDA)

            elif self._code[self._pos] == "\n":
                try:
                    self._set_new_line()
                except StopIteration:
                    break

            elif self._code[self._pos] == ".":
                # maybe ellipsis?
                if self.is_ellipsis(self._code, self._pos):
                    self._pos += 2
                    yield Token("..", TranslatorToken.ELLIPSIS)
                else:
                    self._pos += 1
                    yield Token(".", TranslatorToken.POINT)

            elif self._code[self._pos] == ";":
                self._pos += 1
                yield Token(";", TranslatorToken.SEMICOLON)

            elif self._code[self._pos] == ":":
                self._pos += 1
                yield Token(":", TranslatorToken.COLON)

            elif self._code[self._pos] == ",":
                self._pos += 1
                yield Token(",", TranslatorToken.COMMA)

            elif self._code[self._pos] == "+":
                self._pos += 1
                yield Token("+", TranslatorToken.CONCAT)

            elif self._code[self._pos] == "-":
                self._pos += 1
                yield Token("-", TranslatorToken.MINUS)

            elif self._code[self._pos] == "=":
                self._pos += 1
                yield Token("=", TranslatorToken.ASSIGN)

            elif self._code[self._pos] == "{":
                self._pos += 1
                yield Token("{", TranslatorToken.FP_OP)

            elif self._code[self._pos] == "}":
                self._pos += 1
                yield Token("}", TranslatorToken.FP_CL)

            elif self._code[self._pos] == "[":
                self._pos += 1
                yield Token("[", TranslatorToken.SP_OP)

            elif self._code[self._pos] == "]":
                self._pos += 1
                yield Token("]", TranslatorToken.SP_CL)

            elif self._code[self._pos] == "(":
                self._pos += 1
                yield Token("(", TranslatorToken.RP_OP)

            elif self._code[self._pos] == ")":
                self._pos += 1
                yield Token(")", TranslatorToken.RP_CL)

            elif self._code[self._pos] == "<":
                if self.is_junc():
                    yield Token("<-", TranslatorToken.JUNC)
                else:
                    self.error(
                        msg=f"unexpected symbol.\ntrace:\n{self.get_trace()}"
                        )

            elif self._code[self._pos].isalpha():
                # ID
                yield self.match_symbol(self._code)

            elif self._code[self._pos].isdigit():
                # int | float
                yield self.match_number(self._code)

            elif self._code[self._pos] == "/":
                # comment
                self._skip(self._code[self._pos])

            elif self._code[self._pos] in ("'", '"'):
                # str
                yield self.match_literal(self._code, self._code[self._pos])

            else:
                self.error(
                    msg=f"unexpected symbol.\ntrace:\n{self.get_trace()}"
                    )

        yield Token("EOF", TranslatorToken.EOF)

    def is_junc(self) -> bool:
        if (self._pos + 1) < len(self._code) and self._code[
            self._pos + 1] == "-":
            self._pos += 2
            return True
        return False

    def match_array(self, code: str) -> tuple[Token | None, bool]:
        ptr_pos = self._pos
        if self._match_array(code):
            return Token("ARRAY", TranslatorToken.ARRAY_CONST), True
        # reset cursor position to start
        self._pos = ptr_pos
        return None, False

    def _match_array(
            self,
            code: str,
            *,
            depth: Optional[int] = None,
    ) -> bool:
        _d = depth
        if _d is not None and _d > TYPE_MATCHING_LIMIT:
            self.error(
                    msg=f"type matching depth limit {_d}.\ntrace:\n{self.get_trace()}"
            )

        if _d is None:
            _d = 1

        self._pos += 1
        is_array: bool = True
        ellipsis_possible: bool = True
        comma_possible: bool = True

        while self._pos < len(code) and is_array:
            if code[self._pos] == "[":
                is_array = self._match_array(code, depth=_d + 1)
                self._pos += 1

            elif code[self._pos] == "]":
                return is_array

            elif code[self._pos].isalpha():
                is_array = self._match_type(code)

            elif code[self._pos] == "." and ellipsis_possible:
                if code[self._pos - 1] not in (" ", ",") and self.is_ellipsis(
                        code, self._pos
                ):
                    # comma is impossible if we found ellipsis
                    comma_possible = False
                    self._pos += 2
                    continue
                is_array = False

            elif code[self._pos] == "," and comma_possible:
                self._pos += 1

            elif code[self._pos] == ":" and comma_possible:
                self._pos += 1
                try:
                    st = self._pos
                    self._skip_int(self._code)
                    int(code[st: self._pos])
                    comma_possible = False
                except TypeError:
                    is_array = False

            elif code[self._pos] == " ":
                self._pos += 1

            else:
                return False
        return False

    def _match_type(self, code: str) -> bool:
        symbols: list[str] = []
        while self._pos < len(code) and code[self._pos].isalpha():
            symbols.append(code[self._pos])
            self._pos += 1

        symb = "".join(symbols)
        token = self._reserved_keywords.get(symb)
        if token is None:
            return False
        return token.token_type in (
                TranslatorToken.INT_CONST,
                TranslatorToken.FLOAT_CONST,
                TranslatorToken.BOOL_CONST,
                TranslatorToken.STR_CONST,
        )

    def match_symbol(self, code: str) -> Token:
        """symbols - literals without brackets like LITERAL"""
        symbols: list[str] = []
        while self._pos < len(code):
            if (
                    code[self._pos].isalpha()
                    or code[self._pos].isdigit()
                    or code[self._pos] == "_"
            ):
                symbols.append(code[self._pos])
                self._pos += 1
                continue
            break

        s = "".join(symbols)
        token = self._reserved_keywords.get(s)
        if token is None:
            # we think it is a new literal
            return Token(s, TranslatorToken.ID)
        return token

    def match_number(self, code: str) -> Token:
        pos = self._pos
        while self._pos < len(code) and code[self._pos].isdigit():
            self._pos += 1

        if self._pos < len(code) and code[self._pos] == ".":
            self._pos += 1
            while self._pos < len(code) and code[self._pos].isdigit():
                self._pos += 1

            return Token(float(code[pos: self._pos]), TranslatorToken.FLOAT)
        return Token(int(code[pos: self._pos]), TranslatorToken.INT)

    def _skip_int(self, code: str) -> None:
        while self._pos < len(code) and code[self._pos].isdigit():
            self._pos += 1

    def match_literal(self, code: str, to: str) -> Token:
        st = self._pos
        self._skip(to)
        string = code[st + 1: self._pos - 1]  # skip brackets
        return Token(string, TranslatorToken.STR)

    @staticmethod
    def is_ellipsis(code: str, pos: int) -> bool:
        if (pos + 1) > len(code):
            return False
        return True if code[pos + 1] == "." else False

    def error(self, *, msg: str = "") -> NoReturn:
        raise TranslatorError(msg)


class Parser:
    """build AST from tokens"""

    def __init__(self, tokenizer: Tokenizer, reader: CodeReader) -> None:
        self._tokenizer = tokenizer
        self._reader = reader
        self._tokenizer.set_reader(self._reader)
        self._token: Optional[Token] = None
        try:
            self._tokens = self._tokenizer.get_next_token()
            self._curr_token: Token = next(self._tokens)
        except StopIteration:
            msg = f"unexpected EOF.\ntrace:\n{self._tokenizer.get_trace()}"
            self.error(msg=msg)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(tkn={self._tokenizer}, token={self._curr_token})"

    def eat(self, token: TranslatorToken) -> None:
        """switch to next token (check token sequence validity)"""
        if self._curr_token.token_type == token:
            self._curr_token = next(self._tokens)
            return

        msg = f"Syntax error.\ntrace:\n{self._tokenizer.get_trace()}"
        self.error(msg=msg)

    def translate(self) -> AstNode:
        module: Module = Module(f"Module {self._reader.name}")
        while self._curr_token.token_type != TranslatorToken.EOF:
            if self._curr_token.token_type == TranslatorToken.OBJ_CLASS:
                node = self.object()
                module.add_block(node)

            elif self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                node = self.var_decl()
                module.add_variable(node)

            elif self._curr_token.token_type == TranslatorToken.TEMPL_KW:
                node = self.template()
                module.add_block(node)

            elif self._curr_token.token_type == TranslatorToken.CONN_KW:
                node = self.connection()
                module.add_block(node)

            elif self._curr_token.token_type == TranslatorToken.SIGN_KW:
                node = self.signal()
                module.add_block(node)

        return module

    def object(self) -> AstNode:
        """return block"""
        self.eat(TranslatorToken.OBJ_CLASS)
        obj_type = ObjectType(self._curr_token.value, self._curr_token)
        self.eat(TranslatorToken.OBJ_TYPE)
        base_name, obj_name = self.name()
        scope = self.obj_scope()
        self.eat(TranslatorToken.SEMICOLON)
        obj = Object(base_name, obj_type, name_ext=obj_name)
        for node in scope:
            if node.node_type == TranslatorToken.DIRECTIVE:
                obj.add_directive(node)

            elif node.node_type == TranslatorToken.VARIABLE:
                obj.add_variable(node)

            elif node.node_type == TranslatorToken.PARAM_ASSIGN:
                obj.add_parameter(node)

            elif node.node_type == TranslatorToken.CONNECTION:
                obj.add_connection(node)

            else:
                obj.add_block(node)
        return obj

    def name(self) -> tuple[str, list[AstNode]]:
        _name = []
        base_name = self._curr_token.value
        self.eat(TranslatorToken.ID)
        while self._curr_token.token_type == TranslatorToken.CONCAT:
            self.eat(TranslatorToken.CONCAT)
            _name.append(self.var_extract())
        return base_name, _name

    def var_extract(self) -> AstNode:
        self.eat(TranslatorToken.VAR_SYMB)
        var = self._curr_token
        self.eat(TranslatorToken.ID)
        return Var(var)

    def obj_scope(self) -> list[AstNode]:
        """return block"""
        self.eat(TranslatorToken.FP_OP)
        nodes: list[AstNode] = []
        while self._curr_token.token_type != TranslatorToken.FP_CL:
            if self._curr_token.token_type == TranslatorToken.OBJ_CLASS:
                node = self.object()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                node = self.var_decl()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.SIGN_KW:
                node = self.signal()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.POINT:
                node = self.directive()
                nodes.append(node)

            # skip parameter here -> no grammar

            elif self._curr_token.token_type == TranslatorToken.CONN_KW:
                node = self.connection()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.ID:
                # parameter
                node = self.obj_param()
                nodes.append(node)

        self.eat(TranslatorToken.FP_CL)
        # handle parsed nodes
        return nodes

    def obj_param(self) -> AstNode:
        parameter = Parameter(self._curr_token)
        self.eat(TranslatorToken.ID)
        self.eat(TranslatorToken.COLON)
        par_type = self.type_spec()
        assign = self._curr_token
        self.eat(TranslatorToken.ASSIGN)
        par_value: Optional[AstNode] = None
        declaration = ParamDeclaration(parameter, par_type)
        if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
            par_value = self.var_extract()

        elif self._curr_token.token_type == TranslatorToken.RANGE_KW:
            par_value = self.range()

        else:
            par_value = self.value()  # ID

        options = self.obj_opt()
        self.eat(TranslatorToken.SEMICOLON)
        return ParameterAssign(declaration, assign, par_value, options=options)

    def obj_opt(self) -> list[AstNode]:
        return []

    def var_decl(self) -> AstNode:
        self.eat(TranslatorToken.VAR_SYMB)
        names: list[AstNode] = []
        while self._curr_token.token_type == TranslatorToken.ID:
            var = Var(self._curr_token)
            names.append(var)
            self.eat(TranslatorToken.ID)

            if self._curr_token.token_type != TranslatorToken.COMMA:
                break

            self.eat(TranslatorToken.COMMA)
            self.eat(TranslatorToken.VAR_SYMB)

        self.eat(TranslatorToken.COLON)
        type_spec = self.type_spec()

        declaration = VarDeclaration(names, type_spec)

        if self._curr_token.token_type == TranslatorToken.ASSIGN:
            assign = self._curr_token

            self.eat(TranslatorToken.ASSIGN)
            if self._curr_token.token_type == TranslatorToken.RP_OP:
                # dynamic name
                val_src = self.dyn_name()

            elif self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                val_src = self.var_extract()

            else:
                # value
                val_src = self.value()

            declaration = VarAssign(declaration, assign, val_src)

        self.eat(TranslatorToken.SEMICOLON)
        return declaration

    def dyn_name(self) -> AstNode:
        self.eat(TranslatorToken.RP_OP)
        base = self._curr_token
        name_parts: list[AstNode] = []
        self.eat(TranslatorToken.ID)
        while self._curr_token.token_type == TranslatorToken.CONCAT:
            name = self.var_extract()
            name_parts.append(name)
        self.eat(TranslatorToken.RP_CL)
        dyn_name = DynamicVarName(base, name_parts)
        return dyn_name

    def template(self) -> AstNode:
        self.eat(TranslatorToken.TEMPL_KW)
        templ_name = self._curr_token
        self.eat(TranslatorToken.ID)
        scope = self.templ_scope()
        self.eat(TranslatorToken.SEMICOLON)
        template = Template(templ_name.value)
        for node in scope:
            if node.node_type == TranslatorToken.CONTEXT:
                template.add_context(node)

            elif node.node_type == TranslatorToken.DIRECTIVE:
                template.add_directive(node)

            elif node.node_type == TranslatorToken.VARIABLE:
                template.add_variable(node)

            elif node.node_type == TranslatorToken.PARAMETER:
                template.add_parameter(node)

            elif node.node_type == TranslatorToken.CONNECTION:
                template.add_connection(node)

            else:
                template.add_block(node)

        return template

    def templ_scope(self) -> list[AstNode]:
        self.eat(TranslatorToken.FP_OP)
        nodes: list[AstNode] = []
        while self._curr_token.token_type != TranslatorToken.FP_CL:
            if self._curr_token.token_type == TranslatorToken.OBJ_CLASS:
                node = self.object()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                node = self.var_decl()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.SIGN_KW:
                node = self.signal()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.POINT:
                node = self.directive()
                nodes.append(node)

            # skip parameter here -> no grammar

            elif self._curr_token.token_type == TranslatorToken.CONN_KW:
                node = self.connection()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.POINT:
                node = self.directive()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.CTX_KW:
                node = self.context()
                nodes.append(node)

        self.eat(TranslatorToken.FP_CL)
        return nodes

    def context(self) -> AstNode:
        self.eat(TranslatorToken.CTX_KW)
        ctx_name = self._curr_token  # ID
        self.eat(TranslatorToken.ID)
        scope = self.ctx_scope()
        self.eat(TranslatorToken.SEMICOLON)
        context = Context(ctx_name.value)
        for var in scope:
            context.add_variable(var)
        return context

    def ctx_scope(self) -> list[AstNode]:
        self.eat(TranslatorToken.FP_OP)
        _vars: list[AstNode] = []
        while self._curr_token.token_type != TranslatorToken.FP_CL:
            _vars.append(self.var_decl())

        self.eat(TranslatorToken.FP_CL)
        return _vars

    def signal(self) -> AstNode:
        self.eat(TranslatorToken.SIGN_KW)
        direction = self.s_direct()
        sig_type = self.sign_type()
        base_name, sig_name = self.name()
        scope = self.sign_scope()
        self.eat(TranslatorToken.SEMICOLON)
        signal = Signal(base_name, direction, sig_type, name_ext=sig_name)
        for node in scope:
            if node.node_type == TranslatorToken.DIRECTIVE:
                signal.add_directive(node)

            elif node.node_type == TranslatorToken.VARIABLE:
                signal.add_variable(node)

            elif node.node_type == TranslatorToken.PARAM_ASSIGN:
                signal.add_parameter(node)

            elif node.node_type == TranslatorToken.CONNECTION:
                signal.set_connection(node)

        return signal

    def s_direct(self) -> AstNode:
        d = self._curr_token
        self.eat(TranslatorToken.SIGN_DIRECT)
        return SignalDirection(d.value, d)

    def sign_type(self) -> AstNode:
        t = self._curr_token
        self.eat(TranslatorToken.SIGN_TYPE)
        return SignalType(t.value, t)

    def sign_scope(self) -> list[AstNode]:
        self.eat(TranslatorToken.FP_OP)
        blocks: list[AstNode] = []
        while self._curr_token.token_type != TranslatorToken.FP_CL:
            if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                node = self.var_decl()
                blocks.append(node)

            elif self._curr_token.token_type == TranslatorToken.ID:
                # sign parameter
                node = self.sign_par()
                blocks.append(node)

            elif self._curr_token.token_type == TranslatorToken.POINT:
                node = self.directive()
                blocks.append(node)

            elif self._curr_token.token_type == TranslatorToken.CONN_KW:
                node = self.connection()
                blocks.append(node)

        self.eat(TranslatorToken.FP_CL)
        return blocks

    def sign_par(self) -> AstNode:
        parameter = Parameter(self._curr_token)
        self.eat(TranslatorToken.ID)
        self.eat(TranslatorToken.COLON)
        par_type = self.type_spec()
        assign = self._curr_token
        self.eat(TranslatorToken.ASSIGN)
        par_value: Optional[AstNode] = None
        declaration = ParamDeclaration(parameter, par_type)
        if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
            par_value = self.var_extract()

        elif self._curr_token.token_type == TranslatorToken.RANGE_KW:
            par_value = self.range()

        else:
            par_value = self.value()  # ID

        options = self.s_option()
        self.eat(TranslatorToken.SEMICOLON)
        return ParameterAssign(declaration, assign, par_value, options=options)

    def s_option(self) -> list[AstNode]:
        options: list[AstNode] = []
        while self._curr_token.token_type == TranslatorToken.SIGN_OPT:
            opt_token = self._curr_token
            self.eat(TranslatorToken.SIGN_OPT)

            if self._curr_token.token_type != TranslatorToken.ASSIGN:
                # opt without value
                opt = ParameterOption(opt_token)
                options.append(opt)
                continue

            self.eat(TranslatorToken.ASSIGN)
            par_value: AstNode

            if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                par_value = self.var_extract()

            elif self._curr_token.token_type == TranslatorToken.S_CONST:
                par_value = SystemConstValue(self._curr_token)
                self.eat(TranslatorToken.S_CONST)

            else:
                par_value = self.value()

            opt = ParameterOption(opt_token, value=par_value)
            options.append(opt)
            continue

        return options

    def value(self) -> AstNode:
        """value        : text_value | numeric | bool_value | array
           numeric      : MINUS? INT | FLOAT
           text_value   : STR
           bool_value   : BOOL
           MINUS        : "-"
        """

        token = self._curr_token
        if self._curr_token.token_type in (
        TranslatorToken.MINUS, TranslatorToken.INT, TranslatorToken.FLOAT):
            return self.numeric()

        elif self._curr_token.token_type == TranslatorToken.STR:
            self.eat(TranslatorToken.STR)

        elif self._curr_token.token_type == TranslatorToken.BOOL:
            self.eat(TranslatorToken.BOOL)

        elif self._curr_token.token_type == TranslatorToken.SP_OP:
            return self.array()

        return Value(token)

    def numeric(self) -> AstNode:
        token = self._curr_token
        minus: Optional[Token] = None
        if self._curr_token.token_type == TranslatorToken.MINUS:
            minus = token
            self.eat(TranslatorToken.MINUS)
            token = self._curr_token

        if self._curr_token.token_type == TranslatorToken.INT:
            self.eat(TranslatorToken.INT)

        elif self._curr_token.token_type == TranslatorToken.FLOAT:
            self.eat(TranslatorToken.FLOAT)

        return Value(token, unary_token=minus)

    def array(self) -> AstNode:
        self.eat(TranslatorToken.SP_OP)
        arr_items: list[AstNode] = []
        while self._curr_token.token_type != TranslatorToken.SP_CL:
            arr_items.extend(self.arr_items())

        self.eat(TranslatorToken.SP_CL)
        return ArrayValue(arr_items)

    def arr_items(self) -> list[AstNode]:
        items: list[AstNode] = []
        if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
            items.append(Var(self._curr_token))

        else:
            items.append(self.value())

        while self._curr_token.token_type == TranslatorToken.COMMA:
            self.eat(TranslatorToken.COMMA)

            if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                items.append(Var(self._curr_token))

            else:
                items.append(self.value())

        return items

    def directive(self) -> AstNode:
        self.eat(TranslatorToken.POINT)
        _direct = self.dir_kind()
        self.eat(TranslatorToken.SEMICOLON)
        return _direct

    def dir_kind(self) -> AstNode:
        if self._curr_token.token_type == TranslatorToken.USE_KW:
            return self.use()

        elif self._curr_token.token_type == TranslatorToken.PUT_KW:
            return self.put()

        elif self._curr_token.token_type == TranslatorToken.BIND_KW:
            return self.bind()

    def bind(self) -> AstNode:
        bind_type = self._curr_token
        self.eat(TranslatorToken.BIND_KW)
        ext: Optional[list[AstNode]] = None
        if self._curr_token.token_type == TranslatorToken.RP_OP:
            obj_name, ext = self.comp_name()
        else:
            obj_name = self._curr_token.value
            self.eat(TranslatorToken.ID)
        return BindDirective(bind_type.value, bind_type, obj_name, name_ext=ext)

    def comp_name(self) -> AstNode:
        self.eat(TranslatorToken.RP_OP)
        name = self.name()
        self.eat(TranslatorToken.RP_CL)
        return name

    def put(self) -> AstNode:
        """put          : put_kw in ID from var_extract rule?
           put_kw       : подстановка
           in           : в
           from         : из

        EBNF rule grammar
        """
        put_type = self._curr_token
        self.eat(TranslatorToken.PUT_KW)
        self.eat(TranslatorToken.IN)
        dest = PutIn(self._curr_token)
        self.eat(TranslatorToken.ID)
        self.eat(TranslatorToken.FROM)
        src = PutFrom(self.var_extract())
        rule = None
        if self._curr_token.token_type == TranslatorToken.RULE_KW:
            rule = self.rule()
        return PutDirective(put_type.value, put_type, dest, src, rule=rule)

    def use(self) -> AstNode:
        name = self._curr_token
        self.eat(TranslatorToken.USE_KW)
        dest = UseDest(self._curr_token)
        self.eat(TranslatorToken.ID)
        meth = self.use_method()
        vals_kw = self.vals_kw()
        filter = self.filter()
        use_directive = UseDirective(
                name.value,
                name,
                dest,
                meth,
                vals_kw,
                filter,
        )
        return use_directive

    def rule(self) -> AstNode | None:
        """rule         : rule_kw (rule_expr | var_extract)
           rule_expr    : SP_OP idx HYPHEN idx SP_CL junc SP_OP IT SP_CL
           rule_kw      : правило
        """
        self.eat(TranslatorToken.RULE_KW)
        if self._curr_token.token_type == TranslatorToken.SP_OP:
            return self.rule_expr()

        return self.var_extract()

    def rule_expr(self) -> AstNode:
        self.eat(TranslatorToken.SP_OP)
        _fr = self._curr_token
        self.eat(TranslatorToken.INT)
        self.eat(TranslatorToken.COLON)
        _to = self._curr_token
        self.eat(TranslatorToken.INT)
        self.eat(TranslatorToken.SP_CL)
        self.eat(TranslatorToken.JUNC)
        self.eat(TranslatorToken.SP_OP)
        i_par = self._curr_token
        self.eat(TranslatorToken.IT)
        self.eat(TranslatorToken.SP_CL)
        return PutRule(_fr, _to, i_par)

    def use_method(self) -> AstNode:
        m = self._curr_token
        self.eat(TranslatorToken.USE_METHOD)
        return UseMethod(m)

    def vals_kw(self) -> AstNode:
        v_kw = self._curr_token
        self.eat(TranslatorToken.VALS_KW)
        return UseVals(v_kw)

    def filter(self) -> AstNode:
        kind = self._curr_token
        if self._curr_token.token_type == TranslatorToken.EXCL_KV:
            f_val = self.exclude()
            return UseDirectiveFilter(kind, value=f_val)

        self.eat(TranslatorToken.ALL)
        return UseDirectiveFilter(kind)

    def exclude(self) -> AstNode:
        self.eat(TranslatorToken.EXCL_KV)
        if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
            return self.var_extract()

        return self.value()

    def connection(self) -> AstNode:
        self.eat(TranslatorToken.CONN_KW)
        base_name, conn_name = self.name()
        scope = self.conn_scope()
        self.eat(TranslatorToken.SEMICOLON)
        connection = Connection(base_name, name_ext=conn_name)
        for node in scope:
            if node.node_type == TranslatorToken.DIRECTIVE:
                connection.add_directive(node)

            elif node.node_type == TranslatorToken.VARIABLE:
                connection.add_variable(node)

            else:
                connection.add_parameter(node)

        return connection

    def conn_scope(self) -> list[AstNode]:
        self.eat(TranslatorToken.FP_OP)
        nodes: list[AstNode] = []
        while self._curr_token.token_type != TranslatorToken.FP_CL:
            if self._curr_token.token_type == TranslatorToken.ID:
                node = self.conn_par()
                nodes.append(node)

            elif self._curr_token.token_type == TranslatorToken.POINT:
                node = self.directive()
                nodes.append(node)

        self.eat(TranslatorToken.FP_CL)
        return nodes

    def conn_par(self) -> AstNode:
        param = Parameter(self._curr_token)
        self.eat(TranslatorToken.ID)
        self.eat(TranslatorToken.COLON)
        _par_type = self.type_spec()
        _par_value: Optional[AstNode] = None
        declaration = ParamDeclaration(param, _par_type)
        assign = self._curr_token
        self.eat(TranslatorToken.ASSIGN)

        if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
            _par_value = self.var_extract()

        elif self._curr_token.token_type == TranslatorToken.RANGE_KW:
            _par_value = self.range()

        else:
            _par_value = self.value()

        options = self.conn_opt()
        self.eat(TranslatorToken.SEMICOLON)
        return ParameterAssign(declaration, assign, _par_value, options=options)

    def conn_opt(self) -> list[AstNode]:
        options: list[AstNode] = []
        while self._curr_token.token_type in (TranslatorToken.CONN_OPT,):
            opt_type = self._curr_token
            self.eat(TranslatorToken.CONN_OPT)

            if self._curr_token.token_type != TranslatorToken.ASSIGN:
                # option without parameter
                # create and add option
                option = ParameterOption(opt_type)
                options.append(option)
                continue

            self.eat(TranslatorToken.ASSIGN)
            if self._curr_token.token_type == TranslatorToken.VAR_SYMB:
                opt_value = self.var_extract()

            else:
                opt_value = self.value()

            option = ParameterOption(opt_type, value=opt_value)
            options.append(option)

        return options

    def range(self) -> AstNode:
        is_float = False
        self.eat(TranslatorToken.RANGE_KW)
        self.eat(TranslatorToken.SP_OP)
        token = self._curr_token
        _range: list[AstNode] = [None, None]
        if self._curr_token.token_type == TranslatorToken.TILDA:
            self.eat(TranslatorToken.TILDA)
            _min = TildaValue(token, float("-inf"))
            _range[0] = _min

        elif self._curr_token.token_type == TranslatorToken.VAR_SYMB:
            val = self.var_extract()
            _range[0] = val

        else:
            _range[0] = Value(token)
            self.eat(TranslatorToken.INT)

        self.eat(TranslatorToken.COMMA)
        token = self._curr_token

        if self._curr_token.token_type == TranslatorToken.TILDA:
            self.eat(TranslatorToken.TILDA)
            _max = TildaValue(token, float("+inf"))
            _range[1] = _max

        elif self._curr_token.token_type == TranslatorToken.VAR_SYMB:
            val = self.var_extract()
            _range[1] = val

        else:
            _range[1] = Value(token)
            self.eat(TranslatorToken.INT)

        self.eat(TranslatorToken.SP_CL)
        return Range(_range[0], _range[1])

    def type_spec(self) -> AstNode:
        token = self._curr_token
        if self._curr_token.token_type == TranslatorToken.INT_CONST:
            self.eat(TranslatorToken.INT_CONST)

        elif self._curr_token.token_type == TranslatorToken.FLOAT_CONST:
            self.eat(TranslatorToken.FLOAT_CONST)

        elif self._curr_token.token_type == TranslatorToken.STR_CONST:
            self.eat(TranslatorToken.STR_CONST)

        elif self._curr_token.token_type == TranslatorToken.BOOL_CONST:
            self.eat(TranslatorToken.BOOL_CONST)

        elif self._curr_token.token_type == TranslatorToken.ARRAY_CONST:
            is_arr, spec = self.array_spec()
            if not is_arr:
                self.error(
                    msg=f"Syntax error/\ntrace:\n{self._tokenizer.get_trace()}"
                    )
            return spec
        return _T(token)

    def array_spec(self) -> tuple[bool, AstNode]:
        arr_t = _ArrT()
        arr_t.add_definition(_T(self._curr_token))
        self.eat(TranslatorToken.ARRAY_CONST)
        arr_t.add_definition(_T(self._curr_token))
        self.eat(TranslatorToken.SP_OP)
        while self._curr_token.token_type != TranslatorToken.SP_CL:
            _type = self.type_spec()
            arr_t.add_definition(_type)

            if self._curr_token.token_type == TranslatorToken.COLON:
                arr_t.add_definition(_T(self._curr_token))
                _types_cnt = self.arr_size()
                arr_t.add_definition(_types_cnt)

            elif self._curr_token.token_type == TranslatorToken.ELLIPSIS:
                # we will break, next symbol should be ']'
                arr_t.add_definition(_T(self._curr_token))
                self.eat(TranslatorToken.ELLIPSIS)
                continue

            if self._curr_token.token_type == TranslatorToken.COMMA:
                arr_t.add_definition(_T(self._curr_token))
                self.eat(TranslatorToken.COMMA)

        arr_t.add_definition(_T(self._curr_token))
        self.eat(TranslatorToken.SP_CL)
        return True, arr_t

    def arr_size(self) -> AstNode:
        self.eat(TranslatorToken.COLON)
        sz = Value(self._curr_token)
        self.eat(TranslatorToken.INT)
        return sz

    def error(self, *, msg: str = "") -> NoReturn:
        raise TranslatorError(msg)

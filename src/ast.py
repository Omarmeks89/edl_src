from abc import ABC, abstractmethod
from typing import Any, Optional

from src.exceptions import TranslatorRuntimeError
from src.tokens import TranslatorToken, Token


class AstNode:

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    @property
    # @abstractmethod
    def node_type(self) -> TranslatorToken:
        pass

    @property
    # @abstractmethod
    def name(self) -> str:
        pass

    # @abstractmethod
    def visit(self, visitor: Any) -> Any:
        pass


class Block(AstNode):
    """node class for instances having scope.
    Top level scope"""

    def __init__(self, name: str) -> None:
        self._name = name
        self._vars = []
        self._directives = []
        self._blocks = []

    def add_variable(self, var: AstNode) -> None:
        self._vars.append(var)

    def add_directive(self, _dir: AstNode) -> None:
        self._directives.append(_dir)

    def add_block(self, block: AstNode) -> None:
        self._blocks.append(block)

    def __repr__(self) -> str:
        return (
            f"<{self._name}> (\n"
            f"\tvars: {self._vars},\n"
            f"\tdirectives: {self._directives},\n"
            f"\tblocks: {self._blocks}\n)"
        )

    @property
    @abstractmethod
    def node_type(self) -> TranslatorToken:
        pass

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def visit(self, visitor: Any) -> Any:
        pass


class Module(Block):
    """main program scope (text)"""

    def __init__(self, name: str) -> None:
        super().__init__(name)

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.MODULE

    def get_vars(self) -> list[AstNode]:
        return self._vars

    def get_directives(self) -> list[AstNode]:
        return self._directives

    def get_blocks(self) -> list[AstNode]:
        return self._blocks

    def visit(self, visitor: Any) -> Any:
        visitor.module(self)


class Context(AstNode):

    def __init__(self, name: str) -> None:
        self._name = name
        self._vars: list[AstNode] = []

    def __repr__(self) -> str:
        return f"<{self._name}> (\n" f"\tvars: {self._vars},\n)"

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.CONTEXT

    def get_vars(self) -> list[AstNode]:
        return self._vars

    def add_variable(self, var: AstNode) -> None:
        self._vars.append(var)

    def visit(self, visitor: Any) -> Any:
        # for var in self._vars:
        #     var.visit(visitor)
        visitor.context(self)


class Connection(AstNode):
    """implements connection object"""

    def __init__(
        self,
        name: str,
        *,
        name_ext: Optional[list[AstNode]] = None,
    ) -> None:
        self._name = name
        self._vars: list[AstNode] = []
        self._directives: list[AstNode] = []
        self._params: list[AstNode] = []
        self._name_ext = name_ext

    def __repr__(self) -> str:
        return (
            f"<{self._name}> (\n"
            f"\tvars: {self._vars},\n"
            f"\vparameters: {self._params},\n"
            f"\tdirectives: {self._directives},\n"
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.CONNECTION

    def add_variable(self, var: AstNode) -> None:
        self._vars.append(var)

    def add_directive(self, _dir: AstNode) -> None:
        self._directives.append(_dir)

    def add_parameter(self, param: AstNode) -> None:
        self._params.append(param)

    def get_name_extensions(self) -> list[AstNode]:
        return self._name_ext or []

    def get_vars(self) -> list[AstNode]:
        return self._vars

    def get_directives(self) -> list[AstNode]:
        return self._directives

    def get_params(self) -> list[AstNode]:
        return self._params

    def visit(self, visitor: Any) -> Any:
        visitor.connection(self)


class SignalDirection(AstNode):

    def __init__(self, direction: str, token: Token) -> None:
        self._direction = direction
        self._token = token

    def __repr__(self) -> str:
        return f"{type(self).__name__}(direction={self._direction})"

    def get_direction(self) -> str:
        return self._direction

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.direction(self)


class SignalType(AstNode):

    def __init__(self, _type: str, token: Token) -> None:
        self._type = _type
        self._token = token

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type={self._type})"

    @property
    def type(self) -> str:
        return self._type

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.sig_type(self)


class Signal(AstNode):

    def __init__(
        self,
        name: str,
        direction: AstNode,
        sig_type: AstNode,
        *,
        name_ext: Optional[list[AstNode]] = None,
    ) -> None:
        self._name = name
        self._direction = direction
        self._sig_type = sig_type
        self._vars: list[AstNode] = []
        self._directives: list[AstNode] = []
        self._params: list[AstNode] = []
        self._conn: Optional[AstNode] = None
        self._name_ext = name_ext

    def __repr__(self) -> str:
        return (
            f"<{self._name}> (\n"
            f"\tdirection: {self._direction},\n"
            f"\tsig_type: {self._sig_type},\n"
            f"\tvars: {self._vars},\n"
            f"\vparameters: {self._params},\n"
            f"\tdirectives: {self._directives},\n"
        )

    @property
    def direction(self) -> str:
        return self._direction.get_direction()

    @property
    def sig_type(self) -> str:
        return self._sig_type.type

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.SIGNAL

    def add_variable(self, var: AstNode) -> None:
        self._vars.append(var)

    def add_directive(self, _dir: AstNode) -> None:
        self._directives.append(_dir)

    def add_parameter(self, param: AstNode) -> None:
        self._params.append(param)

    def set_connection(self, conn: AstNode) -> None:
        if self._conn is None:
            self._conn = conn

        raise TranslatorRuntimeError("redefine signal connection not allowed")

    def get_name_extensions(self) -> list[AstNode]:
        return self._name_ext or []

    def get_vars(self) -> list[AstNode]:
        return self._vars

    def get_directives(self) -> list[AstNode]:
        return self._directives

    def get_params(self) -> list[AstNode]:
        return self._params

    def get_connection(self) -> AstNode:
        return self._conn

    def visit(self, visitor: Any) -> Any:
        """process signal object"""
        visitor.signal(self)


class Template(Block):
    """template block (with context)"""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._contexts: list[AstNode] = []
        self._params: list[AstNode] = []
        self._connections: list[AstNode] = []

    def __repr__(self) -> str:
        return (
            f"<{self._name}> (\n"
            f"\tcontexts: {self._contexts},\n"
            f"\tvars: {self._vars},\n"
            f"\tdirectives: {self._directives},\n"
            f"\tconnections: {self._connections},\n"
            f"\tblocks: {self._blocks}\n)"
        )

    def add_context(self, ctx: AstNode) -> None:
        self._contexts.append(ctx)

    def add_parameter(self, param: AstNode) -> None:
        self._params.append(param)

    def add_connection(self, conn: AstNode) -> None:
        self._connections.append(conn)

    def get_vars(self) -> list[AstNode]:
        return self._vars

    def get_directives(self) -> list[AstNode]:
        return self._directives

    def get_blocks(self) -> list[AstNode]:
        return self._blocks

    def get_params(self) -> list[AstNode]:
        return self._params

    def get_contexts(self) -> list[AstNode]:
        return self._contexts

    def get_connections(self) -> list[AstNode]:
        return self._connections

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.TEMPLATE

    def visit(self, visitor: Any) -> Any:
        """process contexts at first"""
        visitor.template(self)


class ObjectType(AstNode):

    def __init__(self, _type: str, token: Token) -> None:
        self._type = _type
        self._token = token

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type={self._type})"

    @property
    def type(self) -> str:
        return self._type

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.obj_type(self)


class Object(Block):
    """node class for instances having scope.
    Top level scope"""

    def __init__(
        self,
        name: str,
        obj_type: AstNode,
        *,
        name_ext: Optional[list[AstNode]] = None,
    ) -> None:
        super().__init__(name)
        self._name_ext = name_ext
        self._obj_type = obj_type
        self._params: list[AstNode] = []
        self._connections: list[AstNode] = []

    def __repr__(self) -> str:
        return (
            f"<{self._name}> (\n"
            f"\ttype: {self._obj_type},\n"
            f"\tvars: {self._vars},\n"
            f"\tdirectives: {self._directives},\n"
            f"\tconnections: {self._connections},\n"
            f"\tblocks: {self._blocks}\n)"
        )

    @property
    def obj_type(self) -> str:
        return self._obj_type.type

    def add_parameter(self, param: AstNode) -> None:
        self._params.append(param)

    def add_connection(self, conn: AstNode) -> None:
        self._connections.append(conn)

    def get_name_extensions(self) -> list[AstNode]:
        return self._name_ext or []

    def get_vars(self) -> list[AstNode]:
        return self._vars

    def get_directives(self) -> list[AstNode]:
        return self._directives

    def get_blocks(self) -> list[AstNode]:
        return self._blocks

    def get_params(self) -> list[AstNode]:
        return self._params

    def get_connections(self) -> list[AstNode]:
        return self._connections

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.OBJECT

    def visit(self, visitor: Any) -> Any:
        """same order as module"""
        visitor.object(self)


class Value(AstNode):

    def __init__(self, token: Token) -> None:
        self._token = token

    def __repr__(self) -> str:
        return f"{type(self).__name__}(val={self._token.value}, type={self._token.token_type})"

    @property
    def value(self) -> Any:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.value(self)


class ArrayValue(AstNode):

    def __init__(self, items: list[AstNode]) -> None:
        self._items = items
        self._type = TranslatorToken.ARRAY

    def __repr__(self) -> str:
        return f"{type(self).__name__}(val={self._items}, type={self._type})"

    @property
    def value(self) -> Any:
        return self._items

    @property
    def node_type(self) -> TranslatorToken:
        return self._type

    def visit(self, visitor: Any) -> Any:
        visitor.array_value(self)


class TildaValue(AstNode):
    """-inf -> +inf"""

    def __init__(self, token: Token, val: float) -> None:
        self._value = val
        self._token = token

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(value={self._value}, type={self._token.token_type})"
        )

    @property
    def value(self) -> Any:
        return self._value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.tilda_value(self)


class SystemConstValue(AstNode):

    def __init__(self, token: Token) -> None:
        self._token = token

    def __repr__(self) -> str:
        return f"{type(self).__name__}(value={self._token.value}, type={self._token.token_type})"

    @property
    def value(self) -> Any:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.system_const_value(self)


# =========================== USE ==============================================


class UseDirectiveFilter(AstNode):

    def __init__(self, kind: Token, *, value: AstNode = None) -> None:
        self._kind = kind
        self._value = value

    @property
    def name(self) -> str:
        return self._kind.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._kind.token_type  # ID

    def visit(self, visitor: Any) -> Any:
        visitor.use_filter(self)


class UseDest(AstNode):

    def __init__(self, token: Token) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type  # ID

    def visit(self, visitor: Any) -> Any:
        visitor.use_dest(self)


class UseMethod(AstNode):

    def __init__(self, token: Token) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type  # USE_METHOD

    def visit(self, visitor: Any) -> Any:
        visitor.use_method(self)


class UseVals(AstNode):
    """значения"""

    def __init__(self, token: Token) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type  # ID

    def visit(self, visitor: Any) -> Any:
        visitor.use_vals(self)


class UseDirective(AstNode):
    """concrete directive Use"""

    def __init__(
        self,
        name: str,
        _type: Token,
        dest_symb: UseDest,
        method: UseMethod,
        vals: UseVals,
        filter: UseDirectiveFilter,
    ) -> None:
        self._name = name
        self._type = _type
        self._dest_symb = dest_symb
        self._method = method
        self._vals = vals
        self._filter = filter

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name}, type={self._type})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def directive_type(self) -> TranslatorToken:
        return self._type.token_type

    def dest(self) -> UseDest:
        return self._dest_symb

    def get_method(self) -> UseMethod:
        return self._method

    def get_vals(self) -> UseVals:
        return self._vals

    def filter(self) -> UseDirectiveFilter:
        return self._filter

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.DIRECTIVE

    def visit(self, visitor: Any) -> Any:
        visitor.use_directive(self)


# ============================== PUT ===========================================
class PutIn(AstNode):
    """put directive dest point"""

    def __init__(self, token: Token) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type  # ID

    def visit(self, visitor: Any) -> Any:
        visitor.put_in(self)


class PutFrom(AstNode):
    """data source for PUT directive"""

    def __init__(self, val: AstNode) -> None:
        self._val = val

    def __repr__(self) -> str:
        return f"{self._val}"

    @property
    def name(self) -> str:
        return self._val.name

    @property
    def node_type(self) -> TranslatorToken:
        return self._val.node_type  # ID

    def visit(self, visitor: Any) -> Any:
        visitor.use_vals(self)


class PutRule(AstNode):

    def __init__(self, st_idx: Token, end_idx: Token, i_par: Token) -> None:
        self._st_idx = st_idx
        self._end_idx = end_idx
        self._i = i_par

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.RULE

    def visit(self, visitor: Any) -> Any:
        visitor.put_rule(self)


class PutDirective(AstNode):
    """implements PUT directive options"""

    def __init__(
        self,
        name: str,
        _type: Token,
        _in: PutIn,
        _from: PutFrom,
        *,
        rule: Optional[PutRule] = None,
    ) -> None:
        self._name = name
        self._type = _type
        self._in = _in
        self._from = _from
        self._rule = rule

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name}, type={self._type})"

    @property
    def name(self) -> str:
        return self._type.value

    def dest(self) -> PutIn:
        return self._in

    def source(self) -> PutFrom:
        return self._from

    def rule(self) -> PutRule | None:
        return self._rule

    @property
    def directive_type(self) -> TranslatorToken:
        return self._type.token_type

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.DIRECTIVE

    def visit(self, visitor: Any) -> Any:
        visitor.put_directive(self)


# =============================== BIND =========================================
class BindDirective(AstNode):

    def __init__(
        self,
        name: str,
        _type: Token,
        base_name: str,
        *,
        name_ext: Optional[list[AstNode]] = None,
    ) -> None:
        self._name = name
        self._type = _type
        self._base_name = base_name
        self._name_ext = name_ext

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name}, type={self._type}, bound={self._name_ext})"

    @property
    def name(self) -> str:
        return self._type.value

    @property
    def directive_type(self) -> TranslatorToken:
        return self._type.token_type

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.DIRECTIVE

    def get_bounded(self) -> list[AstNode]:
        return self._name_ext

    def get_base_name(self) -> str:
        return self._base_name

    def visit(self, visitor: Any) -> Any:
        visitor.bind_directive(self)


class Parameter(AstNode):
    """parameter"""

    def __init__(self, token: Token) -> None:
        self._token = token

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._token.value})"

    @property
    def name(self) -> str:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.PARAMETER

    def visit(self, visitor: Any) -> Any:
        visitor.parameter(self)


class Var(AstNode):
    """variable"""

    def __init__(self, token: Token) -> None:
        self._token = token

    def __repr__(self) -> str:
        return f"<{self._token.value}>"

    @property
    def name(self) -> str:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.var(self)


class _T(AstNode):
    """system type"""

    def __init__(self, token: Token) -> None:
        self._token = token

    def __repr__(self) -> str:
        return f"<type {self._token.token_type.value}>"

    @property
    def name(self) -> str:
        return self._token.value

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.type(self)


class _ArrT(AstNode):
    """system array type"""

    def __init__(self) -> None:
        self._define: list[AstNode] = []

    def add_definition(self, t: AstNode) -> None:
        self._define.append(t)

    def __repr__(self) -> str:
        return f"<type {TranslatorToken.ARRAY_CONST}> ({self._define})"

    @property
    def name(self) -> str:
        return TranslatorToken.ARRAY_CONST.value

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.ARRAY_CONST

    def visit(self, visitor: Any) -> Any:
        visitor.type_arr(self)


class VarDeclaration(AstNode):

    def __init__(self, _vars: list[AstNode], var_type: AstNode) -> None:
        self._vars = _vars
        self._var_type = var_type

    def __repr__(self) -> str:
        return f"{type(self).__name__}(holders={self._vars}, type={self._var_type})"

    @property
    def name(self) -> str:
        return self.__repr__()

    def get_vars(self) -> list[AstNode]:
        return self._vars

    def get_var_type(self) -> AstNode:
        return self._var_type

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.VARIABLE

    def visit(self, visitor: Any) -> Any:
        visitor.var_declaration(self)


class ParamDeclaration(AstNode):

    def __init__(self, param: Parameter, var_type: _T) -> None:
        self._param = param
        self._var_type = var_type

    def __repr__(self) -> str:
        return f"{type(self).__name__}(param={self._param}, type={self._var_type})"

    @property
    def name(self) -> str:
        return self.__repr__()

    def get_param(self) -> AstNode:
        return self._param

    def get_param_type(self) -> AstNode:
        return self._var_type

    @property
    def node_type(self) -> TranslatorToken:
        return self._var_type.node_type

    def visit(self, visitor: Any) -> Any:
        visitor.param_declaration(self)


class DynamicVarName(AstNode):

    def __init__(self, token: Token, name_ext: list[AstNode]) -> None:
        self._base_name = token.value
        self._token = token
        self._name_ext = name_ext

    @property
    def name(self) -> str:
        return f"{self.__repr__()}{self._base_name}"

    def get_name_extensions(self) -> list[AstNode]:
        return self._name_ext

    @property
    def node_type(self) -> TranslatorToken:
        return self._token.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.dynamic_name(self)


class VarAssign(AstNode):

    def __init__(self, var_decl: AstNode, op: Token, value: AstNode) -> None:
        self._var_decl = var_decl
        self._op = op
        self._value = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(decl={self._var_decl}, op={self._op}, v={self._value})"

    @property
    def name(self) -> str:
        return self.__repr__()

    def get_vars_declaration(self) -> VarDeclaration:
        return self._var_decl

    def get_value(self) -> AstNode:
        return self._value

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.VARIABLE

    def visit(self, visitor: Any) -> Any:
        visitor.var_assign(self)


class ParameterOption(AstNode):

    def __init__(self, option: Token, *, value: Optional[AstNode] = None) -> None:
        self._option = option
        self._value = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(opt={self._option.value}, val={self._value}, type={self._option})"

    @property
    def name(self) -> str:
        return self._option.value

    @property
    def value(self) -> AstNode:
        return self._value

    @property
    def node_type(self) -> TranslatorToken:
        return self._option.token_type

    def visit(self, visitor: Any) -> Any:
        visitor.parameter_option(self)


class ParameterAssign(AstNode):

    def __init__(
        self,
        param_decl: AstNode,
        op: Token,
        value: AstNode,
        *,
        options: Optional[list[AstNode]] = None,
    ) -> None:
        self._param_decl = param_decl
        self._op = op
        self._value = value
        self._options = options

    def __repr__(self) -> str:
        return f"{type(self).__name__}(p={self._param_decl}, op={self._op}, v={self._value}, opts={self._options})"

    @property
    def name(self) -> str:
        return self._param_decl.name

    def get_param_decl(self) -> ParamDeclaration:
        return self._param_decl

    def get_param_value(self) -> AstNode:
        return self._value

    def get_options(self) -> list[AstNode]:
        return self._options

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.PARAM_ASSIGN

    def visit(self, visitor: Any) -> Any:
        visitor.parameter_assign(self)


class Range(AstNode):
    """implements range kind"""

    def __init__(self, _min: AstNode, _max: AstNode) -> None:
        self._min = _min
        self._max = _max

    def __repr__(self) -> str:
        return f"{type(self).__name__}(from={self._min}, to={self._max})"

    @property
    def name(self) -> str:
        return f"{type(self).__name__}(from={self._min}, to={self._max})"

    @property
    def node_type(self) -> TranslatorToken:
        return TranslatorToken.RANGE

    @property
    def min(self) -> Any:
        return self._min

    @property
    def max(self) -> Any:
        return self._max

    def visit(self, visitor: Any) -> Any:
        visitor.range(self)

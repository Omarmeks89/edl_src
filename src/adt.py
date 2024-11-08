from abc import abstractmethod
from typing import Optional, Any, Mapping

from src.ast import AstNode, Value, _T, Var, SystemConstValue, Range
from src.exceptions import (
    TranslatorRuntimeError,
    TranslatorParameterError,
    TranslatorTypeError,
)
from src.tokens import TranslatorToken


class Symbol:
    """implement ADT symbol"""

    def __init__(self, name: str, *, _type: Optional[_T] = None) -> None:
        self._name = name
        self._type = _type
        self._value = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> AstNode | None:
        return self._value

    @property
    def node_type(self) -> TranslatorToken:
        return self._type.node_type

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name}, type={self._type})"


class BuiltinSymbol(Symbol):
    """used for types: int, str, bool, array, float"""

    def __init__(self, name: str) -> None:
        super().__init__(name)


class DirectiveSymbol(Symbol):
    """used for directives"""

    def __init__(self, name: str) -> None:
        super().__init__(name)


class VarSymbol(Symbol):
    """used for variables"""

    def __init__(
        self, name: str, *, _type: Optional[Any] = None, value: Optional[Value] = None
    ) -> None:
        super().__init__(name, _type=_type)
        self._value: Optional[Value] = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name}, type={self._type}, val={self._value})"

    @property
    def value(self) -> Any | None:
        if self._value is None:
            return self._value

        value = self._value.value
        if self._value.negative:
            value = -value
        return value

    def set_value(self, value: Value) -> None:
        self._value = value

    def visit(self, visitor: Any) -> None:
        visitor.var_symbol(self)


# =================== options and parameters ===================================


class Option:
    """represent parameter option"""

    def __init__(self, name: str, value: Value | Var | SystemConstValue) -> None:
        self._name = name
        self._value = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name}, value={self._value})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> Any:
        if isinstance(self._value, Var):
            return self._value.name
        elif isinstance(self._value, Value):
            return self._value.value
        elif isinstance(self._value, SystemConstValue):
            return self._value.value
        else:
            raise TranslatorTypeError(f"unsupported option value type: {self._value}")

    @property
    @abstractmethod
    def kind(self) -> TranslatorToken:
        """return kind of option"""
        pass

    @abstractmethod
    def visit(self, visitor: Any) -> None:
        pass


class SignalStatusOption(Option):
    """option Статус of signal object"""

    @property
    def kind(self) -> TranslatorToken:
        return TranslatorToken.SIGN_OPT

    def visit(self, visitor: Any) -> None:
        visitor.sig_status_opt(self)


class SignalReprOption(Option):

    @property
    def kind(self) -> TranslatorToken:
        return TranslatorToken.SIGN_OPT

    def visit(self, visitor: Any) -> None:
        visitor.sig_repr_opt(self)


class SignalSeverityOption(Option):

    @property
    def kind(self) -> TranslatorToken:
        return TranslatorToken.SIGN_OPT

    def visit(self, visitor: Any) -> None:
        visitor.sig_severity_opt(self)


class SignalLabelOption(Option):

    @property
    def kind(self) -> TranslatorToken:
        return TranslatorToken.SIGN_OPT

    def visit(self, visitor: Any) -> None:
        visitor.sig_label_opt(self)


class ConnectionDriverOption(Option):
    """describe connection driver name"""

    @property
    def kind(self) -> TranslatorToken:
        return TranslatorToken.CONN_OPT

    def visit(self, visitor: Any) -> None:
        visitor.conn_driver_opt(self)


# ================================ end of options ==============================


class ParamSymbol(Symbol):
    """used for parameters"""

    _allowed_opt: TranslatorToken

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type)
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name}, type={self._type}, val={self._value}, opts={self._options})"

    @abstractmethod
    def register_option(self, opt: AstNode) -> None:
        pass

    def set_value(self, value: AstNode) -> None:
        self._value = value

    def get_options(self) -> list[AstNode]:
        return self._options

    def visit(self, visitor: Any) -> None:
        visitor.param_symbol(self)


class SignalParamsSymbol(ParamSymbol):
    """base class for signal parameters"""

    _allowed_opt: TranslatorToken = TranslatorToken.SIGN_OPT

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def register_option(self, opt: AstNode) -> None:
        if opt.node_type != self._allowed_opt:
            raise TranslatorParameterError(
                f"invalid option '{opt.name}' for signal parameter"
            )

        if opt.name in self._registered:
            raise TranslatorRuntimeError(
                f"option '{opt.name}' should be registered once"
            )

        self._registered.add(opt.name)
        self._options.append(opt)

    @abstractmethod
    def visit(self, visitor: Any) -> None:
        pass


class SignalParamId(SignalParamsSymbol):
    """id option"""

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")

        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_param_id(self)


class SignalEquipId(SignalParamsSymbol):
    """param Оборудование"""

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_equipment_id(self)


class SignalValue(SignalParamsSymbol):
    """param Значение"""

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def register_option(self, opt: AstNode) -> None:
        if opt.node_type != self._allowed_opt:
            raise TranslatorParameterError(
                f"invalid option '{opt.name}' for signal parameter"
            )

        if opt.name in self._registered:
            raise TranslatorRuntimeError(
                f"option '{opt.name}' should be registered once"
            )

        if opt.name == "статус":
            opt = SignalStatusOption(opt.name, opt.value)

        elif opt.name == "отображать":
            opt = SignalReprOption(opt.name, opt.value)

        elif opt.name == "метка":
            opt = SignalLabelOption(opt.name, opt.value)

        elif opt.name == "важность":
            opt = SignalSeverityOption(opt.name, opt.value)

        else:
            raise TranslatorRuntimeError(f"unexpected signal parameter option {opt}")

        self._registered.add(opt.name)
        self._options.append(opt)

    def visit(self, visitor: Any) -> None:
        visitor.signal_value(self)


class SignalFormula(SignalParamsSymbol):
    """param Формула"""

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_formula(self)


class SignalBaseDescription(SignalParamsSymbol):

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_base_descr(self)


class SignalFormat(SignalParamsSymbol):

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_format(self)


class SignalAck(SignalParamsSymbol):

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_ack(self)


class SignalPersistent(SignalParamsSymbol):

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_persistent(self)


class SignalUnits(SignalParamsSymbol):

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.signal_unit(self)


# ============================== for connection ================================


class ConnectionParamsSymbol(ParamSymbol):
    """base class for connection options"""

    _allowed_opt: TranslatorToken = TranslatorToken.CONN_OPT

    def register_option(self, opt: AstNode) -> None:
        if opt.node_type != self._allowed_opt:
            raise TranslatorParameterError(
                f"invalid option '{opt.name}' for connection parameter"
            )

        if opt.name in self._registered:
            raise TranslatorRuntimeError(
                f"option '{opt.name}' should be registered once"
            )

        self._registered.add(opt.name)
        self._options.append(opt)

    @abstractmethod
    def visit(self, visitor: Any) -> None:
        # visitor.conn_params_symbol(self)
        pass


class ConnectionId(ConnectionParamsSymbol):

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.connection_id(self)


class ConnectionAddress(ConnectionParamsSymbol):
    """for connection address"""

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def register_option(self, opt: AstNode) -> None:
        if opt.node_type != self._allowed_opt:
            raise TranslatorParameterError(
                f"invalid option '{opt.name}' for connection parameter"
            )

        if opt.name in self._registered:
            raise TranslatorRuntimeError(
                f"option '{opt.name}' should be registered once"
            )

        if opt.name == "обработчик":
            opt = ConnectionDriverOption(opt.name, opt.value)

        self._registered.add(opt.name)
        self._options.append(opt)

    def visit(self, visitor: Any) -> None:
        visitor.connection_address(self)


# =========================== equipment params =================================


class EquipmentParamsSymbol(ParamSymbol):
    """base class for equipment parameters"""

    _allowed_opt: TranslatorToken = TranslatorToken.CONN_OPT

    def register_option(self, opt: AstNode) -> None:
        if opt.node_type != self._allowed_opt:
            raise TranslatorParameterError(
                f"invalid option '{opt.name}' for connection parameter"
            )

        self._options.append(opt)

    @abstractmethod
    def visit(self, visitor: Any) -> None:
        pass

    # visitor.equip_params_symbol(self)


class EquipmentId(EquipmentParamsSymbol):
    """represent equipment Id parameter"""

    def __init__(
        self,
        name: str,
        *,
        _type: Optional[Any] = None,
        value: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, _type=_type, value=value)
        if isinstance(value, Range):
            raise TranslatorTypeError(f"range is not supported for '{name}' parameter")
        self._value = value
        self._options: list[AstNode] = []
        self._registered: set[str] = set()

    def visit(self, visitor: Any) -> None:
        visitor.equipment_id(self)


# ================================ data tables =================================


class AbstractDataTable:
    """resolving symbols, build scopes.
    Scope -> TEMPLATE, MODULE, SIGNAL, CONNECTION, OBJECT
    """

    # set of allowed params for scope
    _allowed_params: set = set()

    def __init__(
        self,
        name: str,
        scope_type: TranslatorToken,
        *,
        enclosed_scope: Optional["AbstractDataTable"] = None,
    ) -> None:
        self._name = name
        self._scope_type = scope_type
        self._enclosed_scope = enclosed_scope
        self._symbols: Mapping[str, Symbol] = {}
        self._params: Mapping[str, list[Symbol]] = {}
        self._binded: Optional[AbstractDataTable] = None
        self._ctx: Optional["ContextScope"] = None

    def __repr__(self) -> str:
        return (f"{type(self).__name__}({self._name}, "
                f"{self._scope_type}, {type(self._enclosed_scope)}, "
                f"symbs={self._symbols}, params={self._params}, "
                f"ctx={self._ctx})")

    @property
    def name(self) -> str:
        return self._name

    @property
    def scope_type(self) -> TranslatorToken:
        return self._scope_type

    def get_parameters(self) -> list[Symbol]:
        """return all declared parameters"""
        params = []
        for _, v in self._params.items():
            params.extend(v)
        return params

    def get_enclosed_scope(self) -> Optional["AbstractDataTable"]:
        return self._enclosed_scope

    def get_context(self) -> Optional["ContextScope"]:
        return self._ctx

    def set_context(self, ctx: "ContextScope") -> None:
        if self._ctx is None:
            self._ctx = ctx
            return
        raise TranslatorRuntimeError(f"attempt to redefine context: {ctx.name}")

    def init_builtins(self) -> None:
        """init types: INT, STR, FLOAT, BOOL, ARRAY"""
        self.declare(
            TranslatorToken.INT_CONST.value,
            BuiltinSymbol(TranslatorToken.INT_CONST.value),
        )
        self.declare(
            TranslatorToken.STR_CONST.value,
            BuiltinSymbol(TranslatorToken.STR_CONST.value),
        )
        self.declare(
            TranslatorToken.FLOAT_CONST.value,
            BuiltinSymbol(TranslatorToken.FLOAT_CONST.value),
        )
        self.declare(
            TranslatorToken.BOOL_CONST.value,
            BuiltinSymbol(TranslatorToken.BOOL_CONST.value),
        )
        self.declare(
            TranslatorToken.ARRAY_CONST.value,
            BuiltinSymbol(TranslatorToken.ARRAY_CONST.value),
        )

    def declare(self, sym_name: str, symbol: Symbol) -> None:
        """declare -> for variables"""
        if sym_name in self._symbols:
            raise TranslatorRuntimeError(f"attempt to redefine symbol '{sym_name}' in scope '{self._name}'")
        self._symbols[sym_name] = symbol

    @abstractmethod
    def declare_parameter(self, param_name: str, param: Symbol) -> None:
        """declare parameter and check that param is allowed for scope"""
        pass

    def lookup(self, sym_name: str, *, only_curr: bool = False) -> Symbol | None:
        """lookup for VARIABLE
        If value is returned, symbol is declared
        only_curr - lookup only in current scope.
        """
        symbol = self._symbols.get(sym_name)
        if symbol is None:
            # if nothing in symbols let`s try to find in
            # context and resolve name
            if self._ctx is not None:
                symbol = self._ctx.lookup(sym_name)

        if only_curr:
            return symbol

        if symbol is None and self._enclosed_scope is not None:
            # we dont found in current scope, let`s check enclosed (if exists)
            return self._enclosed_scope.lookup(sym_name)

        return symbol

    def lookup_param(self, sym_name: str) -> Symbol | None:
        """lookup for VARIABLE
        If value is returned, symbol is declared
        """
        symbol = self._params.get(sym_name)
        if symbol is None and self._enclosed_scope is not None:
            # goto enclosed scope
            return self._enclosed_scope.lookup(sym_name)

        return symbol

    def lookup_context(self, ctx_name: str) -> Optional["ContextScope"]:
        if self._ctx is not None and self._ctx.name == ctx_name:
            return self._ctx

        if self._enclosed_scope is not None:
            return self._enclosed_scope.lookup_context(ctx_name)

    def context_found(self) -> bool:
        if self._ctx is not None:
            return True

        if self._enclosed_scope is not None:
            return self._enclosed_scope.context_found()

    @abstractmethod
    def visit(self, visitor: Any) -> None:
        pass


class ModuleScope(AbstractDataTable):
    """global scope. module-level"""

    def __init__(
        self,
        name: str,
        scope_type: TranslatorToken,
    ) -> None:
        super().__init__(name, scope_type)

    def declare_parameter(self, param_name: str, param: Symbol) -> None:
        """nothing at the moment"""
        pass

    def visit(self, visitor: Any) -> None:
        visitor.module(self)


class EquipmentTable(AbstractDataTable):
    """describe equipment symbols table"""

    _allowed_params: set = {
        "Идентификатор",
    }

    def __init__(
        self,
        name: str,
        scope_type: TranslatorToken,
        equip_type: str,
        *,
        enclosed_scope: Optional["AbstractDataTable"] = None,
    ) -> None:
        super().__init__(name, scope_type, enclosed_scope=enclosed_scope)
        self._name_ext: list[VarSymbol] = []
        self._equip_type = equip_type

    @property
    def equipment_type(self) -> str:
        return self._equip_type

    def set_name_extensions(self, ext: list[VarSymbol]) -> None:
        self._name_ext = ext

    def get_name_extensions(self) -> list[VarSymbol]:
        return self._name_ext

    def declare_parameter(self, param_name: str, param: Symbol) -> None:
        if param_name not in self._allowed_params:
            raise TranslatorRuntimeError(
                f"impossible parameter '{param_name}' for scope {self._scope_type}"
            )
        if self._params.get(param_name) is None:
            self._params[param_name] = []
        self._params[param_name].append(param)

    def visit(self, visitor: Any) -> None:
        visitor.equipment_table(self)


class Link:
    """represent link between objects"""

    def __init__(self, name: str, obj: AbstractDataTable) -> None:
        self._name = name
        self._obj = obj

    @property
    def object(self) -> AbstractDataTable:
        return self._obj

    @abstractmethod
    def visit(self, visitor: Any) -> None:
        pass


class ConnectionLink(Link):
    """special link for connection instance"""

    def visit(self, visitor: Any) -> None:
        visitor.conn_link(self)


class SignalTable(AbstractDataTable):
    """scope and allowed symbols for signal"""

    _allowed_params: set = {
        "Идентификатор",
        "Единицы",
        "Значение",
        "Описание0",
        "Описание1",
        "Описание2",
        "Описание3",
        "Формула",
        "Формат",
        "Квитируемый",
        "Журналируемый",
        "Оборудование",
    }

    def __init__(
        self,
        name: str,
        scope_type: TranslatorToken,
        sig_type: str,
        sig_direction: str,
        *,
        enclosed_scope: Optional[Link] = None,
    ) -> None:
        super().__init__(name, scope_type, enclosed_scope=enclosed_scope)
        self._name_ext: list[VarSymbol] = []
        self._binded: Optional["AbstractDataTable"] = None
        self._sig_type = sig_type
        self._sig_direction = sig_direction

    @property
    def signal_type(self) -> str:
        return self._sig_type

    @property
    def link(self) -> AbstractDataTable | None:
        return self._binded

    def set_name_extensions(self, ext: list[VarSymbol]) -> None:
        self._name_ext = ext

    def get_name_extensions(self) -> list[VarSymbol]:
        return self._name_ext

    def declare_parameter(self, param_name: str, param: Symbol) -> None:
        if param_name not in self._allowed_params:
            raise TranslatorRuntimeError(
                f"impossible parameter '{param_name}' for scope {self._scope_type}"
            )
        if self._params.get(param_name) is None:
            self._params[param_name] = []
        self._params[param_name].append(param)

    def bind_to(self, b: "AbstractDataTable") -> None:
        if self._binded is None and id(self) != id(b):
            self._binded = ConnectionLink(b.name, b)

    def visit(self, visitor: Any) -> None:
        visitor.signal_table(self)


class ConnectionTable(AbstractDataTable):
    """scope and allowed symbols for connection"""

    _allowed_params: set = {
        "Идентификатор",
        "Адрес",
    }

    def __init__(
        self,
        name: str,
        scope_type: TranslatorToken,
        *,
        enclosed_scope: Optional["AbstractDataTable"] = None,
    ) -> None:
        super().__init__(name, scope_type, enclosed_scope=enclosed_scope)
        self._name_ext: list[VarSymbol] = []

    def set_name_extensions(self, ext: list[VarSymbol]) -> None:
        self._name_ext = ext

    def get_name_extensions(self) -> list[VarSymbol]:
        return self._name_ext

    def declare_parameter(self, param_name: str, param: Symbol) -> None:
        if param_name not in self._allowed_params:
            raise TranslatorRuntimeError(
                f"impossible parameter '{param_name}' for scope {self._scope_type}"
            )
        if self._params.get(param_name) is None:
            self._params[param_name] = []
        self._params[param_name].append(param)

    def visit(self, visitor: Any) -> None:
        visitor.connection_table(self)


class ContextScope:
    """specific scope for context"""

    def __init__(
        self,
        name: str,
    ) -> None:
        self._name = name
        self._symbols: Mapping[str, VarSymbol] = {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(s={self._symbols})"

    @property
    def name(self) -> str:
        return self._name

    def declare(self, sym_name: str, symbol: VarSymbol) -> None:
        """declare -> for variables"""
        if sym_name is self._symbols:
            raise TranslatorRuntimeError(
                f"attempt to redefine context symbol '{sym_name}'"
            )
        self._symbols[sym_name] = symbol

    def get_symbol_keys(self) -> list[str]:
        return [k for k in self._symbols.keys()]

    def set_value(self, sym_name: str, val: Value):
        var = self._symbols.get(sym_name)
        if var is None:
            raise TranslatorRuntimeError(f"var '{sym_name}' not declared in context")
        var: VarSymbol
        var.set_value(val)

    def lookup(self, sym_name: str, *, only_curr: bool = False) -> VarSymbol | None:
        """lookup for VARIABLE
        If value is returned, symbol is declared
        """
        # print(f"WELCOME TO CTX: {self._name}: {self.__repr__()}")
        return self._symbols.get(sym_name)

    @staticmethod
    def context_found(self) -> bool:
        return True

    def visit(self, visitor: Any) -> None:
        visitor.context_table(self)


class TemplateScope(AbstractDataTable):
    """specific scope for template (with contexts)"""

    def __init__(
        self,
        name: str,
        scope_type: TranslatorToken,
        *,
        enclosed_scope: Optional["AbstractDataTable"] = None,
    ) -> None:
        super().__init__(name, scope_type, enclosed_scope=enclosed_scope)
        self._contexts: Mapping[str, ContextScope] = {}

    def set_context(self, name: str, ctx: ContextScope) -> None:
        if self._contexts.get(name):
            raise TranslatorRuntimeError(
                f"redefine declared context '{name}' not allowed"
            )
        self._contexts[name] = ctx

    def declare_parameter(self, param_name: str, param: Symbol) -> None:
        """no template param at the moment"""
        pass

    def lookup_ctx(self, ctx_name: str, sym_name: str) -> Any | None:
        """lookup wished context"""
        ctx = self._contexts.get(ctx_name)
        if ctx is None:
            return None
        return ctx.lookup(sym_name)

    def lookup(self, sym_name: str, *, only_curr: bool = False) -> Symbol | None:
        """lookup for VARIABLE
        If value is returned, symbol is declared
        """
        symbol = self._symbols.get(sym_name)
        if symbol is None:
            for v in self._contexts.values():
                symbol = v.lookup(sym_name)
                if symbol is not None:
                    return symbol

        if only_curr:
            return symbol

        if symbol is None and self._enclosed_scope is not None:
            # goto enclosed scope
            return self._enclosed_scope.lookup(sym_name)
        return symbol

    def lookup_context(self, ctx_name: str) -> Optional["ContextScope"]:
        """no contexts possible over Template"""
        if ctx_name in self._contexts:
            return self._contexts.get(ctx_name)
        return None

    def context_found(self) -> bool:
        return True if self._contexts else False

    def visit(self, visitor: Any) -> None:
        visitor.template_scope(self)


class _NotInit(Symbol):
    """represent that symbol is not initialized"""

    def __repr__(self) -> str:
        return f"NOT_INIT({self._name}:{self._type})"

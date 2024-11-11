"""
проход визитора готовит данные и генераторы для их
обработки (если есть контексты) или запускает сборщика
если контекстов нет.

Те на каждую итерацию контекста создается один объекст, который
берет из него данные.
"""

from typing import Mapping, Any, Optional, Generator

from src.adt import (
    EquipmentId,
    AbstractDataTable,
    ContextScope,
    ModuleScope,
    TemplateScope,
    VarSymbol,
    EquipmentTable,
    ConnectionTable,
    SignalTable,
    Symbol,
    ParamSymbol,
    _NotInit,
    SignalParamId,
    SignalEquipId,
    SignalValue,
    SignalFormula,
    SignalBaseDescription,
    SignalFormat,
    SignalAck,
    SignalUnits,
    SignalPersistent,
    ConnectionId,
    ConnectionAddress,
)
from src.ast import (
    Module,
    Context,
    Template,
    Object,
    Connection,
    Signal,
    VarDeclaration,
    ParamDeclaration,
    VarAssign,
    ParameterAssign,
    ParameterOption,
    _ArrT,
    PutDirective,
    PutRule,
    UseDirective,
    Range,
    Var,
    Value,
    ArrayValue,
    AstNode,
    BindDirective, DynamicVarName,
)
from src.exceptions import (
    TranslatorTypeError,
    TranslatorRuntimeError,
    TranslatorDirectiveError,
)
from src.tokens import TranslatorToken
from src.translator import Parser
from translators.finalizer import TranslationFinalizer


class AdtBuilder:
    """part of compiler that build ADT tables"""

    def __init__(self, parser: Parser) -> None:
        self._parser = parser
        self._curr_scope: Optional[AbstractDataTable] = None
        self._scopes: Mapping[str, AbstractDataTable] = {}

        # use for next resolving and compilation stage
        # directive use is owner here
        self._ctx_listeners: Mapping[str, list[AbstractDataTable]] = {}
        self._ctx_resolvers: Mapping[str, ContextResolver] = {}

        self._type_matcher = TypeMatcher()

    def run(self, translator: TranslationFinalizer) -> TranslationFinalizer:
        # ADT building stage
        module = self._parser.translate()
        module.visit(self)

        # compilation stage (using ADT)
        to_del = []
        for r in self._ctx_resolvers.values():
            ctx_name = r.get_ctx_name()
            for _ in r.get_resolver():
                listeners = self._ctx_listeners.get(ctx_name)
                if listeners is None:
                    continue

                for listener in listeners:
                    listener.visit(translator)
                    to_del.append(listener.name)

            if ctx_name in self._ctx_listeners:
                # current context is resolved
                del self._ctx_listeners[ctx_name]

        for d in to_del:
            if d in self._scopes:
                del self._scopes[d]

        for k, v in self._scopes.items():
            v.visit(translator)

        return translator

    def module(self, m: Module) -> None:
        scope = self._scopes.get(m.name)
        if scope is None:
            module_scope = ModuleScope(m.name, m.node_type)
            self._scopes[m.name] = module_scope
            self._curr_scope = module_scope

        for var in m.get_vars():
            var.visit(self)

        for d in m.get_directives():
            d.visit(self)

        for block in m.get_blocks():
            block.visit(self)

    def context(self, ctx: Context) -> None:
        # declare context into current scope
        # declare vars and push them into the scope
        if not isinstance(self._curr_scope, TemplateScope):
            raise TranslatorTypeError(
                f"invalid scope type for context: {self._curr_scope}"
            )

        ctx_scope = ContextScope(ctx.name)
        self._curr_scope.set_context(ctx.name, ctx_scope)
        templ_scope = self._curr_scope

        # redefine scope temporary
        self._curr_scope = ctx_scope
        for v in ctx.get_vars():
            v.visit(self)

        self._curr_scope = templ_scope

    def template(self, t: Template) -> None:
        print(f"{t.name}")
        enclosed_scope = self._curr_scope
        template = self._scopes.get(t.name)
        if template is None:
            template = TemplateScope(t.name, t.node_type, enclosed_scope=enclosed_scope)
            self._scopes[t.name] = template
            self._curr_scope = template

        for ctx in t.get_contexts():
            ctx.visit(self)

        for var in t.get_vars():
            var.visit(self)

        for d in t.get_directives():
            d.visit(self)

        for p in t.get_params():
            p.visit(self)

        for conn in t.get_connections():
            print("into connections")
            conn.visit(self)

        for block in t.get_blocks():
            block.visit(self)

        self._curr_scope = enclosed_scope

    def object(self, o: Object) -> None:
        enclosed_scope = self._curr_scope
        eq_scope = self._scopes.get(o.name)
        if eq_scope is None:
            eq_scope = EquipmentTable(
                o.name, o.node_type, o.obj_type, enclosed_scope=enclosed_scope,
            )
            n_ext = o.get_name_extensions()
            for n in n_ext:
                if self._curr_scope.lookup(n.name):
                    continue
                raise TranslatorRuntimeError(
                    f"var '{n.name}' not found for dynamic name"
                )

            eq_scope.set_name_extensions(n_ext)
            self._scopes[o.name] = eq_scope
            self._curr_scope = eq_scope

        for var in o.get_vars():
            var.visit(self)

        for d in o.get_directives():
            d.visit(self)

        for p in o.get_params():
            p.visit(self)

        for conn in o.get_connections():
            conn.visit(self)

        for block in o.get_blocks():
            block.visit(self)

        self._curr_scope = enclosed_scope

    def connection(self, c: Connection) -> None:
        # TODO add full name for valid object registration
        init_conn: bool = True
        enclosed_scope = self._curr_scope
        
        # resolve name at first
        n_ext = c.get_name_extensions()
        r_symbols = []
        for n in n_ext:
            resolving = self._curr_scope.lookup(n.name)
            if resolving is None:
                raise TranslatorRuntimeError(
                    f"var '{n.name}' not found for dynamic name"
                )
            if resolving.value is None:
                raise TranslatorRuntimeError(
                    f"name resolve from context (symbol '{resolving.name}') not allowed"
                )
            r_symbols.append(resolving.value)

        c_name = f"{c.name}{''.join([f'{name}' for name in r_symbols])}"

        conn = self._scopes.get(c_name)
        if conn is None:
            init_conn = False
            conn = ConnectionTable(c.name, c.node_type, enclosed_scope=enclosed_scope)
            conn.set_name(c_name)

        self._curr_scope.declare(c_name, conn)
        self._scopes[c_name] = conn
        self._curr_scope = conn

        if not init_conn:
            for var in c.get_vars():
                var.visit(self)

            for d in c.get_directives():
                d.visit(self)

            for p in c.get_params():
                p.visit(self)

        self._curr_scope = enclosed_scope

    def dynamic_name(self, dn: DynamicVarName) -> None:
        print(f"DYNAMIC VAR NAME: {dn=}")
        pass

    def signal(self, s: Signal) -> None:
        enclosed_scope = self._curr_scope
        signal_scope = self._scopes.get(s.name)
        if signal_scope is None:
            signal_scope = SignalTable(
                s.name,
                s.node_type,
                s.sig_type,
                s.direction,
                enclosed_scope=enclosed_scope,
            )
            n_ext = s.get_name_extensions()
            r_symbols = []
            not_resolved = []
            for n in n_ext:
                resolving = self._curr_scope.lookup(n.name)
                if resolving is None:
                    raise TranslatorRuntimeError(
                        f"var '{n.name}' not found for dynamic name"
                    )
                if resolving.value is not None:
                    r_symbols.append(resolving.value)
                    continue

                # context is not resolved at the moment
                not_resolved.append(n)

            sig_name = f"{s.name}{''.join([f'{name}' for name in r_symbols])}"
            signal_scope.set_name_extensions(not_resolved)
            self._scopes[sig_name] = signal_scope
            self._curr_scope = signal_scope

        for var in s.get_vars():
            var.visit(self)

        for d in s.get_directives():
            d.visit(self)

        for p in s.get_params():
            p.visit(self)

        conn = s.get_connection()
        if conn is not None:
            conn.visit(self)

        self._curr_scope = enclosed_scope

    def var_declaration(self, vd: VarDeclaration) -> None:
        """return var name"""
        # register all vars in current scope with type
        t = vd.get_var_type()
        for v in vd.get_vars():
            # if var name declared raise error
            # lookup all scopes
            if self._curr_scope.lookup(v.name):
                raise TranslatorRuntimeError(f"attempt to redefine registered var name '{v.name}'")
            var_symbol = VarSymbol(v.name, _type=t)
            self._curr_scope.declare(var_symbol.name, var_symbol)

    def param_declaration(self, pd: ParamDeclaration) -> None:
        # register parameter in current scope with type
        p = pd.get_param()
        sig_par = None
        if self._curr_scope.scope_type == TranslatorToken.SIGNAL:
            if p.name == "Идентификатор":
                sig_par = SignalParamId(p.name, _type=pd.get_param_type())

            elif p.name == "Оборудование":
                sig_par = SignalEquipId(p.name, _type=pd.get_param_type())

            elif p.name == "Значение":
                sig_par = SignalValue(p.name, _type=pd.get_param_type())

            elif p.name == "Формула":
                sig_par = SignalFormula(p.name, _type=pd.get_param_type())

            elif p.name in ("Описание0", "Описание1", "Описание2", "Описание3"):
                sig_par = SignalBaseDescription(p.name, _type=pd.get_param_type())

            elif p.name == "Формат":
                sig_par = SignalFormat(p.name, _type=pd.get_param_type())

            elif p.name == "Квитируемый":
                sig_par = SignalAck(p.name, _type=pd.get_param_type())

            elif p.name == "Журналируемый":
                sig_par = SignalPersistent(p.name, _type=pd.get_param_type())

            elif p.name == "Единицы":
                sig_par = SignalUnits(p.name, _type=pd.get_param_type())

        elif self._curr_scope.scope_type == TranslatorToken.CONNECTION:
            if p.name == "Идентификатор":
                sig_par = ConnectionId(p.name, _type=pd.get_param_type())

            elif p.name == "Адрес":
                sig_par = ConnectionAddress(p.name, _type=pd.get_param_type())

        elif self._curr_scope.scope_type == TranslatorToken.OBJECT:
            if p.name == "Идентификатор":
                sig_par = EquipmentId(p.name, _type=pd.get_param_type())

        if sig_par is not None:
            self._curr_scope.declare_parameter(sig_par.name, sig_par)

    def var(self, v: Var) -> None:
        """lookup in current scope or context only"""
        if not self._curr_scope.lookup(v.name):
            raise TranslatorRuntimeError(f"variable '{v.name}' not declared")

    def var_assign(self, va: VarAssign) -> None:
        # first check variable is declared in current scope
        # check value type with var type
        # declare variables
        decl = va.get_vars_declaration()
        value = va.get_value()

        # check declared symbol (vor var_extract)
        value.visit(self)

        # declare current symbols
        decl.visit(self)
        for v in decl.get_vars():
            # TODO add lookup only for current scope
            declared = self._curr_scope.lookup(v.name, only_curr=True)
            if declared is None:
                raise TranslatorRuntimeError(f"variable {v.name} not found")

            if value.node_type == TranslatorToken.ID:
                # var name
                _value = self._curr_scope.lookup(value.name)
                if _value is None:
                    raise TranslatorRuntimeError(f"{__name__}: symbol '{value.name}' not resolved")

                value = _value

            declared: VarSymbol
            # check assigned value type
            if not self._type_matcher.type_match(declared, value):
                raise TranslatorTypeError(
                    f"declared {declared.node_type} got {value.node_type}"
                )

            declared.set_value(value)

    def value(self, value: Value) -> None:
        """handling value. Set unary (if unary)"""
        pass

    def array_value(self, arr: ArrayValue) -> None:
        """handling array value"""
        pass

    def type_arr(self, ta: _ArrT) -> None:
        pass

    def parameter_assign(self, pa: ParameterAssign) -> None:
        # check types
        # check that options are possible
        # declare parameter and add into json
        par_value = pa.get_param_value()
        par_value.visit(self)
        pd: ParamDeclaration = pa.get_param_decl()

        # declare parameter
        pd.visit(self)
        param_sym = pd.get_param()

        declared = self._curr_scope._params.get(param_sym.name)
        if declared is None:
            raise TranslatorRuntimeError(f"parameter '{param_sym.name}' not declared ({pa=})")

        for par in declared:
            par: ParamSymbol
            if par_value.node_type == TranslatorToken.ID:
                # we use variable as a value container
                node = self._curr_scope.lookup(par_value.name)
                if node is None:
                    raise TranslatorRuntimeError(
                        f"variable '{par_value.name}' not initialized"
                    )

                if node.value is None:
                    # mark node that wasn`t initialized
                    par_value = _NotInit(node.name, _type=node._type)

                # we`re expecting that values are resolved at the moment
                else:
                    # par_value = node.value
                    par_value = node

            if par.value is not None:
                continue

            if not self._type_matcher.type_match(par, par_value):
                raise TranslatorTypeError(f"declared {par.node_type} got {par_value}")

            par.set_value(par_value)
            for opt in pa.get_options():
                # collect options
                # check option in builtins for current expression type
                par.register_option(opt)

    def parameter_option(self, po: ParameterOption) -> None:
        pass

    def bind_directive(self, bd: BindDirective) -> None:
        """bind to connection DataTable"""

        # TODO: it should be registered into scope by full name
        # (with name extensions if exists)
        names = bd.get_bounded()
        name_parts = []
        if names is not None:
            for name in names:
                declared = self._curr_scope.lookup(name.name)
                if declared is not None:
                    name_parts.append(declared.value)
                    continue

                raise TranslatorRuntimeError(f"symbol '{name.name}' not resolved")

        full_name = f"{bd.get_base_name()}{''.join([f'{n}' for n in name_parts])}"
        bounded_obj: ConnectionTable = self._curr_scope.lookup(full_name)
        if bounded_obj is None:
            raise TranslatorRuntimeError(
                f"object by full name {full_name} not resolved. DynamicNameError"
                )

        if self._curr_scope.scope_type == TranslatorToken.SIGNAL:
            self._curr_scope.bind_to(bounded_obj)

    def put_directive(self, pd: PutDirective) -> None:
        """directive-unpacker"""
        # check that symbol declared in scope
        data_src = pd.source()
        dest_ctx = pd.dest()
        value = self._curr_scope.lookup(data_src.name)
        if value is None:
            raise TranslatorDirectiveError(f"symbol '{data_src.name}' not resolved")

        ctx = self._curr_scope.lookup_context(dest_ctx.name)
        if ctx is None:
            raise TranslatorDirectiveError(f"context '{dest_ctx.name}' not resolved")

        ctx_keys = ctx.get_symbol_keys()
        resolver = ContextResolver(ctx, ctx_keys, value)
        self._ctx_resolvers[ctx.name] = resolver

    def put_rule(self, pr: PutRule) -> None:
        pass

    def use_directive(self, ud: UseDirective) -> None:
        # subscribe current scope on ctx
        dest = ud.dest()
        listeners = self._ctx_listeners.get(dest.name)
        if listeners is None:
            self._ctx_listeners[dest.name] = []
        self._ctx_listeners[dest.name].append(self._curr_scope)

        ctx = self._curr_scope.lookup_context(dest.name)
        if ctx is None:
            return None

        self._curr_scope.set_context(ctx)

    def range(self, r: Range) -> None:
        pass


class TypeMatcher:
    """responsibility for type resolving"""

    def type_match(self, symb: Symbol, value: AstNode) -> bool:
        """match declared type with current.
        value should be an interface
        """
        FLOAT = (
            TranslatorToken.FLOAT_CONST,
            TranslatorToken.FLOAT,
            TranslatorToken.RANGE,
        )
        INT = (TranslatorToken.INT_CONST, TranslatorToken.INT, TranslatorToken.RANGE)
        STR = (TranslatorToken.STR_CONST, TranslatorToken.STR)
        BOOL = (TranslatorToken.BOOL_CONST, TranslatorToken.BOOL)

        if symb.node_type == TranslatorToken.FLOAT_CONST:
            return True if value.node_type in FLOAT else False

        elif symb.node_type == TranslatorToken.INT_CONST:
            return True if value.node_type in INT else False

        elif symb.node_type == TranslatorToken.BOOL_CONST:
            return True if value.node_type in BOOL else False

        elif symb.node_type == TranslatorToken.STR_CONST:
            return True if value.node_type in STR else False

        elif symb.node_type == TranslatorToken.ARRAY_CONST:
            return self.match_array(symb, value)

    def match_array(self, symb: Symbol, value: AstNode) -> bool:
        """fake implementation"""
        return True


class ContextResolver:
    """generator, that will update ctx with new values"""

    def __init__(self, ctx: ContextScope, ctx_keys: list[str], value_src: Any) -> None:
        self._ctx = ctx
        self._keys = ctx_keys
        self._value_src = value_src
        self._matcher = TypeMatcher()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(ctx={self._ctx}, keys={self._keys})"

    def get_ctx_name(self) -> str:
        return self._ctx.name

    def get_resolver(self) -> Generator[None, None, None]:
        """generator, that doesn`t return anything, only set ctx"""

        # now waiting [[str:6, int:2]..]
        values = (v.value for v in self._value_src.value)
        for value in values:
            if len(value) != len(self._keys):
                raise TranslatorDirectiveError(
                    f"array symbols count not match to context {self._ctx.name}"
                )

            for idx, val in enumerate(value):
                declared = self._ctx.lookup(self._keys[idx])
                if declared is None:
                    raise TranslatorRuntimeError(
                        f"context symbol '{self._keys[idx]}' not resolved"
                    )

                if not self._matcher.type_match(declared, val):
                    raise TranslatorTypeError(f"declared {declared} got {val}")

                self._ctx.set_value(declared.name, val)

            yield

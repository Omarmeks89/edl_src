import pathlib
from abc import ABC, abstractmethod

from src._ast import ParameterOption
from src.adt import (
    AbstractDataTable,
    ConnectionAddress,
    ConnectionDriverOption,
    ConnectionId,
    ConnectionLink,
    ConnectionTable,
    ContextScope,
    EquipmentId,
    EquipmentTable,
    ModuleScope,
    ParamSymbol,
    SignalAck,
    SignalBaseDescription,
    SignalEquipId,
    SignalFormat,
    SignalFormula,
    SignalLabelOption,
    SignalParamId,
    SignalPersistent,
    SignalReprOption,
    SignalSeverityOption,
    SignalStatusOption,
    SignalTable,
    SignalUnits,
    SignalValue,
    Symbol,
    TemplateScope,
    VarSymbol,
)


class BaseFinalizer:
    """Inversion of control to define own finalizers in wished format"""

    def module(self, m: ModuleScope) -> None:
        pass

    def var_symbol(self, vs: VarSymbol) -> None:
        pass

    def param_symbol(self, ps: ParamSymbol) -> None:
        pass

    def sig_status_opt(self, sso: SignalStatusOption) -> None:
        pass

    def sig_repr_opt(self, sro: SignalReprOption) -> None:
        pass

    def sig_severity_opt(self, sso: SignalSeverityOption) -> None:
        pass

    def sig_label_opt(self, slo: SignalLabelOption) -> None:
        pass

    def signal_param_id(self, sps: SignalParamId) -> None:
        pass

    def signal_equipment_id(self, sps: SignalEquipId) -> None:
        pass

    def signal_value(self, sps: SignalValue) -> None:
        pass

    def signal_formula(self, sps: SignalFormula) -> None:
        pass

    def signal_base_descr(self, sps: SignalBaseDescription) -> None:
        pass

    def signal_format(self, sps: SignalFormat) -> None:
        pass

    def signal_ack(self, sps: SignalAck) -> None:
        pass

    def signal_persistent(self, sps: SignalPersistent) -> None:
        pass

    def signal_unit(self, sps: SignalUnits) -> None:
        pass

    def conn_driver_opt(self, cdo: ConnectionDriverOption) -> None:
        pass

    def conn_link(self, cl: ConnectionLink) -> None:
        pass

    def connection_id(self, cps: ConnectionId) -> None:
        pass

    def connection_address(self, cps: ConnectionAddress) -> None:
        pass

    def parameter_option(self, po: ParameterOption) -> None:
        pass

    def equipment_id(self, eps: EquipmentId) -> None:
        pass

    def equipment_table(self, et: EquipmentTable) -> None:
        pass

    def signal_table(self, st: SignalTable) -> None:
        pass

    def connection_table(self, ct: ConnectionTable) -> None:
        pass

    def context_table(self, cs: ContextScope) -> None:
        pass

    def template_scope(self, ts: TemplateScope) -> None:
        pass

    def visit(self, o: Symbol | AbstractDataTable) -> None:
        o.visit(self)

    def write(self, *, output_path: str | pathlib.Path | None = None) -> None:
        pass

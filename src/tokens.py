from enum import Enum
from typing import Any


class TranslatorToken(str, Enum):
    EOF: str = "EOF"
    ID: str = "ID"
    INT: str = "INT"
    FLOAT: str = "FLOAT"
    STR: str = "STR"
    BOOL: str = "BOOL"
    ARRAY: str = "ARRAY"
    ARRAY_CONST: str = "ARRAY_CONST"
    VAR_SYMB: str = "$"
    SEMICOLON: str = ";"
    POINT: str = "."
    COLON: str = ":"
    COMMA: str = ","
    CONCAT: str = "+"
    HYPHEN: str = "-"
    ASSIGN: str = "ASSIGN"
    FP_OP: str = "FP_OP"
    FP_CL: str = "FP_CL"
    SP_OP: str = "SP_OP"
    SP_CL: str = "SP_CL"
    RP_OP: str = "RP_OP"
    RP_CL: str = "RP_CL"
    OBJ_TYPE: str = "OBJ_TYPE"
    OBJ_CLASS: str = "OBJ_CLASS"
    TEMPL_KW: str = "TEMPL_KW"
    CTX_KW: str = "CTX_KW"
    CONN_OPT: str = "CONN_OPT"
    SIGN_OPT: str = "SIGN_OPT"
    SIGN_KW: str = "SIGN_KW"
    CONN_KW: str = "CONN_KW"
    SIGN_DIRECT: str = "SIGN_DIRECT"
    SIGN_TYPE: str = "SIGN_TYPE"
    DIR_KIND: str = "DIR_KIND"
    USE_KW: str = "USE_KW"
    USE_METHOD: str = "USE_METHOD"
    VALS_KW: str = "VALS_KW"
    EXCL_KV: str = "EXCL_KW"
    BIND_KW: str = "BIND_KW"
    ALL: str = "ALL"
    PUT_KW: str = "PUT_KW"
    RULE_KW: str = "RULE_KW"
    IN: str = "IN"
    FROM: str = "FROM"
    IDX: str = "IDX"
    JUNC: str = "JUNC"
    IT: str = "IT"
    INT_CONST: str = "INT_CONST"
    FLOAT_CONST: str = "FLOAT_CONST"
    STR_CONST: str = "STR_CONST"
    BOOL_CONST: str = "BOOL_CONST"
    ELLIPSIS: str = "ELLIPSIS"
    TILDA: str = "TILDA"
    RANGE_KW: str = "RANGE_KW"
    EMPTY: str = "EMPTY"

    # exact Ast node types
    OBJECT: str = "OBJECT"
    MODULE: str = "MODULE"
    TEMPLATE: str = "TEMPLATE"
    DIRECTIVE: str = "DIRECTIVE"
    VARIABLE: str = "VARIABLE"
    PARAMETER: str = "PARAMETER"
    CONTEXT: str = "CONTEXT"
    CONNECTION: str = "CONNECTION"
    SIGNAL: str = "SIGNAL"
    RULE: str = "RULE"
    VAR_ASSIGN: str = "VAR_ASSIGN"
    PARAM_ASSIGN: str = "PARAM_ASSIGN"
    VAR_DECLARATION: str = "VAR_DECLARATION"
    RANGE: str = "RANGE"
    DYNAMIC_NAME: str = "DYNAMIC_NAME"

    S_CONST: str = "S_CONST"

    # token for unary operation
    MINUS: str = "MINUS"


class Token:
    """lexer token"""

    def __init__(self, value: Any, _type: TranslatorToken) -> None:
        self._value = value
        self._type = _type

    def __repr__(self) -> str:
        return f"{type(self).__name__}(val={self._value}, type={self._type})"

    @property
    def token_type(self) -> TranslatorToken:
        return self._type

    @property
    def value(self) -> Any:
        return self._value

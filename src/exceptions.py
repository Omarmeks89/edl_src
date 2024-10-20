class TranslatorError(Exception):
    """Base translator app exception."""

    pass


class PreprocessorError(TranslatorError):
    """any error in preprocessor"""

    pass


class TranslatorRuntimeError(TranslatorError):
    """when we can`t continue operation in runtime"""

    pass


class TranslatorTypeError(TranslatorError):
    """in types mismatch"""

    pass


class TranslatorParameterError(TranslatorError):
    """raises if got unexpected parameter"""

    pass


class TranslatorDirectiveError(TranslatorError):
    """raises when directive failed"""

    pass

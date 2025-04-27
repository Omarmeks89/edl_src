from typing import Any

import pytest
from assertpy import assert_that

from src.exceptions import PreprocessorError
from src.stree import stree


@pytest.mark.parametrize(
        "symbol, l_symbol, value, result",
        (
                (
                        "data",
                        "data",
                        42,
                        42,
                ),
                (
                        "data",
                        "dat",
                        "-",
                        None,
                ),
        ),
)
def test_stree_handle_symbols(
        symbol: str,
        l_symbol: str,
        value: Any,
        result: Any | None,
) -> None:
    """No error handling here"""
    stree_ = stree()
    stree_.add(symbol, value)

    res = stree_.find(l_symbol)
    assert_that(res).is_equal_to(result)


@pytest.mark.parametrize(
        "symbol, l_symbol, value, result",
        (
                (
                        "data",
                        "data",
                        42,
                        42,
                ),
                (
                        "data",
                        "da",
                        42,
                        None,
                ),
        ),
)
def test_stree_find_value_step_by_step(
        symbol: str,
        l_symbol: str,
        value: Any,
        result: Any | None,
) -> None:
    stree_ = stree()
    stree_.add(symbol, value)

    val: Any | None = None
    for s in l_symbol:
        # emulate situation when we read symbol by
        # symbol in preprocessor try to find symbol value
        val = stree_.resolve(s)

    # we`re waiting for val will be equal to value
    assert_that(val).is_equal_to(result)


def test_stree_raises_error_if_value_is_None() -> None:
    st = stree()
    with pytest.raises(PreprocessorError):
        st.add("a", None)

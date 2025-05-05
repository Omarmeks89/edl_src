import pytest
from assertpy import assert_that

from src.exceptions import TranslatorError
from src.symbols_graph import orgnode


def test_sym_graph_return_valid_pointers() -> None:
    root = orgnode.create("root", 0)
    n = root.add("nested_1", 1)

    assert_that(n).is_not_none()
    assert_that(n()).is_not_none()


def test_sym_graph_return_correct_value() -> None:
    root = orgnode.create("root", 0)
    n = root.add("nested_1", 1)
    n = n().add("nested_2", 2)

    root_value = n().get_root_value()

    assert_that(root_value).is_equal_to(0)


def test_sym_graph_return_root_value_if_its_root() -> None:
    root = orgnode.create("root", 0)
    assert_that(root.get_root_value()).is_equal_to(0)


def test_sym_graph_raises_error_if_node_name_not_unique() -> None:
    root = orgnode.create("root", 0)
    root.add("nested_1", 1)

    with pytest.raises(TranslatorError):
        root.add("nested_1", 100500)

import pytest
from assertpy import assert_that

from src.preprocessor import grabber


@pytest.mark.parametrize(
    "code, res",
    (
        ("$a: int = A;", "a"),
        ("    $test_2: int = 0;", "test_2"),
        ("Идентификатор: str = 'id';", "Идентификатор"),
    ),
)
def test_grabber_grab_symbol_from_code_line(code: str, res: str) -> None:
    symbol = grabber.grab_symbol_from_code_line(code)

    assert_that(symbol).is_equal_to(res)

import pytest
from assertpy import assert_that

from src.code_reader import CodeReader
from src.preprocessor import make_preprocessor


def test_preprocessor_handle_simple_code() -> None:
    code = ["#define A 10\n", "#define B\n", "$data: int = A;\n"]
    res = ["\n", "\n", "$data: int = 10;\n"]

    reader = CodeReader("")
    reader.set_cache(code)
    make_preprocessor(reader).process()

    assert_that(reader.code).is_equal_to(res)


@pytest.mark.parametrize(
    "code, res",
    (
        (["# define A 10000\n", "$v: int = A;\n"], ["\n", "$v: int = 10000;\n"]),
        (["# define DATA 1\n", "$v: int = DATA;\n"], ["\n", "$v: int = 1;\n"]),
        (
            ["# define DATA 1\n", "/ $v: int = DATA; /\n"],
            ["\n", "/ $v: int = DATA; /\n"],
        ),  # skip substitutions inside a comment
    ),
)
def test_preprocessor_replace_macro_symbols_correct(
    code: list[str],
    res: list[str],
) -> None:
    reader = CodeReader("test.edl")
    reader.set_cache(code)
    make_preprocessor(reader).process()

    assert_that(reader.code).is_equal_to(res)


@pytest.mark.parametrize(
    "code, res",
    (
        (
            ["/ $a: str = 'path/data/data.json'; /"],
            ["/ $a: str = 'path/data/data.json'; /"],
        ),
        (
            [
                "/ сигнал выходной аналог_р Тест { Формула: str = 'formula{a + b} / {c + d}'; }; /"
            ],
            [
                "/ сигнал выходной аналог_р Тест { Формула: str = 'formula{a + b} / {c + d}'; }; /"
            ],
        ),
        (
            ["#define A 100500\n", "/$b: int = A;\n/\n", "$a: int = A;\n"],
            ["\n", "/$b: int = A;\n/\n", "$a: int = 100500;\n"],
        ),
        (
            [
                '#define B "VALUE"\n',
                'Формула: str = "formula{%, %}" параметр=B параметр=B;\n',
            ],
            [
                "\n",
                'Формула: str = "formula{%, %}" параметр="VALUE" параметр="VALUE";\n',
            ],
        ),
    ),
)
def test_preprocessor_skip_macro_symbols_correct(
    code: list[str],
    res: list[str],
) -> None:
    reader = CodeReader("test.edl")
    reader.set_cache(code)
    make_preprocessor(reader).process()

    assert_that(reader.code).is_equal_to(res)

from assertpy import assert_that

from src.code_reader import CodeReader
from src.preprocessor import TextProcessor, make_processor


def test_preprocessor_replace_symbol() -> None:
    """replace DATA on 10"""

    code = "$data: int = DATA;"
    tp = TextProcessor(None, None, None)

    res = tp.replace_code_line(code[:13], "10")
    assert_that(res).is_equal_to("$data: int = 10;\n")


def test_preprocessor_handle_simple_code() -> None:
    code = ["#define A 10\n", "#define B\n", "$data: int = A;"]
    res = ["\n", "\n", "$data: int = 10;\n"]

    reader = CodeReader("")
    reader.set_cache(code)
    make_processor(reader).process()

    assert_that(reader.code).is_equal_to(res)

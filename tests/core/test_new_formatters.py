from codehem.core.formatting import IndentFormatter, BraceFormatter


def test_indent_formatter_basic():
    fmt = IndentFormatter()
    src = "line1\n    line2"
    result = fmt.apply_indentation(src, "    ")
    assert result.splitlines()[0] == "    line1"


def test_brace_formatter_dedent():
    fmt = BraceFormatter()
    src = "{\n    inner;\n}"
    result = fmt.apply_indentation(src, "")
    assert result.splitlines()[0] == "{"

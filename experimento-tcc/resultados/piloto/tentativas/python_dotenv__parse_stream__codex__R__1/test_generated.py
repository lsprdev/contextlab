from io import StringIO

import pytest

from dotenv.parser import parse_stream


def binding_fields(binding):
    assert isinstance(binding.error, bool)
    return binding.key, binding.value, binding.original.string, binding.original.line, binding.error


def parse_text(text):
    return [binding_fields(binding) for binding in parse_stream(StringIO(text, newline=""))]


@pytest.mark.parametrize("text", ["", "\ufeff"])
def test_empty_input_produces_no_bindings(text):
    assert parse_text(text) == []


@pytest.mark.parametrize("text", [" ", "\n\r\n\r \t", "\u00a0\u2028\t"])
def test_whitespace_only_input_preserves_the_original_text(text):
    assert parse_text(text) == [(None, None, text, 1, False)]


@pytest.mark.parametrize(
    ("text", "key", "value"),
    [
        ("NAME=value", "NAME", "value"),
        ("\t NAME  \t= \tvalue with spaces \t", "NAME", "value with spaces"),
        ("X-Y.1/$:é=ação 🌱", "X-Y.1/$:é", "ação 🌱"),
        ("'name with # and = inside' \t= ok", "name with # and = inside", "ok"),
        (r"'a\b'=ok", r"a\b", "ok"),
        ('"NAME"=value', '"NAME"', "value"),
        ("NAME", "NAME", None),
        ("NAME \t # comment", "NAME", None),
        ("NAME#comment", "NAME", None),
        ("NAME=", "NAME", ""),
        ("NAME= \t", "NAME", ""),
        ("NAME=''", "NAME", ""),
        ('NAME=""', "NAME", ""),
        ("export\tNAME=value", "NAME", "value"),
        ("export\u00a0NAME\u2003=\u00a0value\u2003", "NAME", "value"),
        ("export NAME", "NAME", None),
        ("export=value", "export", "value"),
        ("export", "export", None),
        ("exported=value", "exported", "value"),
        ("EXPORT=value", "EXPORT", "value"),
        ("export export=value", "export", "value"),
        ("# NAME=ignored # still a comment", None, None),
        (" \t# comment", None, None),
        ("NAME=#literal # comment", "NAME", "#literal"),
        ("NAME=#", "NAME", "#"),
        ("NAME= # comment", "NAME", ""),
        ("NAME=\t#comment", "NAME", ""),
        ("NAME=\u2003#comment", "NAME", ""),
        ("NAME=one#two\t# first # second", "NAME", "one#two"),
        ("NAME=one\u00a0#comment", "NAME", "one"),
        ("NAME=a=b=c", "NAME", "a=b=c"),
        ("NAME=left\u2028right", "NAME", "left\u2028right"),
        (r'NAME=raw\n\#tag ${OTHER} "literal"', "NAME", r'raw\n\#tag ${OTHER} "literal"'),
        ("NAME='  a # b  '#comment", "NAME", "  a # b  "),
        ('NAME="  a # b  "\t# comment', "NAME", "  a # b  "),
    ],
)
def test_binding_syntax(text, key, value):
    assert parse_text(text) == [(key, value, text, 1, False)]


@pytest.mark.parametrize(
    ("text", "value"),
    [
        (r'''A="\\ \" \' \a \b \f \n \r \t \v"''', "\\ \" ' \a \b \f \n \r \t \v"),
        (r'''A="\q \x41 \u0042 \0 \/ \8 é"''', r"\q \x41 \u0042 \0 \/ \8 é"),
        (r"""A='\\ \' \" \a \b \f \n \r \t \v'""", "\\ ' " + r'\" \a \b \f \n \r \t \v'),
        (r"""A='\q \x41 \u0042 \0 \/ \8 é'""", r"\q \x41 \u0042 \0 \/ \8 é"),
        (r'''A="ends\\"# comment''', "ends\\"),
        (r"""A='ends\\'# comment""", "ends\\"),
        (r'''A="left\\\"right"''', 'left\\"right'),
        (r"""A='left\\\'right'""", "left\\'right"),
        (r'''A="\\n"''', r"\n"),
        (r'''A="\n"''', "\n"),
    ],
)
def test_quoted_value_escape_rules(text, value):
    assert parse_text(text) == [("A", value, text, 1, False)]


@pytest.mark.parametrize("newline", ["\n", "\r", "\r\n"])
def test_assignment_and_export_do_not_consume_the_next_line(newline):
    empty_assignment = "EMPTY= \t" + newline
    export_alone = "export" + newline
    next_assignment = "NEXT=ok" + newline
    bare_key = "BARE"
    assert parse_text(empty_assignment + export_alone + next_assignment + bare_key) == [
        ("EMPTY", "", empty_assignment, 1, False),
        ("export", None, export_alone, 2, False),
        ("NEXT", "ok", next_assignment, 3, False),
        ("BARE", None, bare_key, 4, False),
    ]


def test_line_numbers_and_original_text_with_multiline_bindings():
    initial_comment = "\r\n \t# primeira\r"
    double_quoted = '\t\n \tA="α\\\nβ\r\nγ\rδ\\n" # comment\r\n'
    single_quoted = "'nome\r\n # = interno'='um\\\rdois\ntrês' \n"
    last_assignment = "\nEND=ok\r"
    trailing_whitespace = " \t\r\n "
    assert parse_text(
        initial_comment + double_quoted + single_quoted + last_assignment + trailing_whitespace
    ) == [
        (None, None, initial_comment, 1, False),
        ("A", "α\\\nβ\r\nγ\rδ\n", double_quoted, 3, False),
        ("nome\r\n # = interno", "um\\\rdois\ntrês", single_quoted, 8, False),
        ("END", "ok", last_assignment, 12, False),
        (None, None, trailing_whitespace, 14, False),
    ]


@pytest.mark.parametrize(
    ("text", "key", "value", "original"),
    [
        ("\ufeffA=é", "A", "é", "A=é"),
        ("\ufeff\ufeffA=1", "\ufeffA", "1", "\ufeffA=1"),
        (" \ufeffA=1", "\ufeffA", "1", " \ufeffA=1"),
        ("A=x\ufeffy", "A", "x\ufeffy", "A=x\ufeffy"),
        ("A=x\ufeff", "A", "x\ufeff", "A=x\ufeff"),
        ("\ufeff\nA=1", "A", "1", "\nA=1"),
    ],
)
def test_only_one_bom_at_the_start_is_removed(text, key, value, original):
    assert parse_text(text) == [(key, value, original, 1, False)]


@pytest.mark.parametrize(
    "malformed",
    [
        "=missing_key",
        "''=empty_key",
        "'unclosed_key=value",
        "two keys=value",
        'A="unterminated',
        "A='unterminated",
        'A="closed"suffix',
        "A='closed' suffix",
        "export =missing_key",
        "export export A=value",
    ],
)
def test_malformed_bindings_at_eof_and_recovery_on_the_next_line(malformed):
    assert parse_text(malformed) == [(None, None, malformed, 1, True)]

    invalid_line = " \t" + malformed + "\n"
    next_line = "NEXT=ok"
    assert parse_text(invalid_line + next_line) == [
        (None, None, invalid_line, 1, True),
        ("NEXT", "ok", next_line, 2, False),
    ]


def test_error_recovery_preserves_source_slices_across_crlf():
    first = "FIRST=ok\r\n"
    invalid = "\n \tBROKEN='valid' extra\r"
    recovered = "\nAFTER=right\r\n"
    last = "FINAL"
    assert parse_text(first + invalid + recovered + last) == [
        ("FIRST", "ok", first, 1, False),
        (None, None, invalid, 2, True),
        ("AFTER", "right", recovered, 4, False),
        ("FINAL", None, last, 6, False),
    ]


def test_recovery_after_a_multiline_value_with_an_invalid_suffix():
    malformed = 'A="first\nsecond" trailing\r'
    next_line = "NEXT=ok"
    assert parse_text(malformed + next_line) == [
        (None, None, malformed, 1, True),
        ("NEXT", "ok", next_line, 3, False),
    ]


def test_iterator_reads_from_the_current_stream_position_when_advanced():
    ignored = "IGNORED=gone\n"
    stream = StringIO(ignored + "FIRST=one\nSECOND=two")
    bindings = parse_stream(stream)
    stream.seek(len(ignored))

    assert iter(bindings) is bindings
    assert binding_fields(next(bindings)) == ("FIRST", "one", "FIRST=one\n", 1, False)
    assert binding_fields(next(bindings)) == ("SECOND", "two", "SECOND=two", 2, False)
    with pytest.raises(StopIteration):
        next(bindings)

from io import StringIO

import pytest

from dotenv.parser import parse_stream


def parsed(source):
    return [
        (binding.key, binding.value, binding.original.string, binding.original.line, binding.error)
        for binding in parse_stream(StringIO(source, newline=""))
    ]


@pytest.mark.parametrize("source", ["", "\ufeff"])
def test_empty_stream_yields_no_bindings(source):
    assert parsed(source) == []


def test_leading_bom_is_removed_once():
    source = "\ufeffFIRST=\ufeffinside\n\ufeffSECOND=end"
    assert parsed(source) == [
        ("FIRST", "\ufeffinside", "FIRST=\ufeffinside\n", 1, False),
        ("\ufeffSECOND", "end", "\ufeffSECOND=end", 2, False),
    ]
    assert parsed("\ufeff\ufeffKEY=value") == [
        ("\ufeffKEY", "value", "\ufeffKEY=value", 1, False),
    ]


@pytest.mark.parametrize(
    ("source", "key", "value"),
    [
        ("\t export\t'clé # = name' \t=\t valeur \t# commentaire\r\n", "clé # = name", "valeur"),
        ("exported=yes", "exported", "yes"),
        ("export=no", "export", "no"),
        ("export\n", "export", None),
        ("export FLAG # comment\r", "FLAG", None),
        ("FLAG# comment", "FLAG", None),
        ("EMPTY=", "EMPTY", ""),
        ("EMPTY= \t\r\n", "EMPTY", ""),
        ("EMPTY=''", "EMPTY", ""),
        ('EMPTY=""', "EMPTY", ""),
        ("X=#literal", "X", "#literal"),
        ("X=\t # comment", "X", ""),
        ("X=\u00a0# comment", "X", ""),
        ("X=#literal # comment", "X", "#literal"),
        ("X=part#literal\t# comment", "X", "part#literal"),
        ("X=one  two\tthree  ", "X", "one  two\tthree"),
        (r"X=one=two\n${OTHER}", "X", r"one=two\n${OTHER}"),
        ("X=' # kept '   # ignored", "X", " # kept "),
        ('X=" # kept "#ignored', "X", " # kept "),
        ("'  spaced  '=yes", "  spaced  ", "yes"),
    ],
)
def test_binding_syntax(source, key, value):
    assert parsed(source) == [(key, value, source, 1, False)]


def test_non_assignment_bindings_and_duplicate_keys_preserve_order_and_source():
    comment = "\r\n \t# comment\r"
    first = "\n  SAME=first\n"
    second = "SAME=second\r\n"
    trailing = "\t\n  "
    assert parsed(comment + first + second + trailing) == [
        (None, None, comment, 1, False),
        ("SAME", "first", first, 3, False),
        ("SAME", "second", second, 5, False),
        (None, None, trailing, 6, False),
    ]


@pytest.mark.parametrize("source", [" \t", "\r\n \n\t\r"])
def test_whitespace_only_stream_yields_one_binding(source):
    assert parsed(source) == [(None, None, source, 1, False)]


def test_comments_at_eof_and_export_followed_by_a_comment():
    first = "export \t# FIRST=ignored\n"
    last = "  # SECOND=ignored"
    assert parsed(first + last) == [
        (None, None, first, 1, False),
        (None, None, last, 2, False),
    ]


def test_single_quoted_values_decode_only_backslash_and_single_quote():
    source = r"""X='café\\path\'s\n\t\a\"\q'"""
    expected = r"""café\path's\n\t\a\"\q"""
    assert parsed(source) == [("X", expected, source, 1, False)]


def test_double_quoted_values_decode_supported_escapes_and_preserve_other_text():
    source = r'''X="café\\\'\"\a\b\f\n\r\t\v\q\x41\u0042${OTHER}"'''
    expected = "café" + "\\'\"\a\b\f\n\r\t\v" + r"\q\x41\u0042${OTHER}"
    assert parsed(source) == [("X", expected, source, 1, False)]


@pytest.mark.parametrize("quote", ["'", '"'])
def test_escaped_backslash_before_closing_quote(quote):
    first = f"PATH={quote}folder\\\\{quote} # comment\n"
    assert parsed(first + "NEXT=ok") == [
        ("PATH", "folder\\", first, 1, False),
        ("NEXT", "ok", "NEXT=ok", 2, False),
    ]


@pytest.mark.parametrize("quote", ["'", '"'])
def test_backslash_before_a_physical_newline_in_a_quoted_value(quote):
    first = f"X={quote}one\\\ntwo{quote}\n"
    assert parsed(first + "NEXT=ok") == [
        ("X", "one\\\ntwo", first, 1, False),
        ("NEXT", "ok", "NEXT=ok", 3, False),
    ]


def test_multiline_values_and_mixed_line_endings():
    header = "# header\r\n"
    single = "\r  A='one\r\ntwo\nthree\rfour'\t# tail\r\n"
    double = 'B="left\nright"\r'
    escaped_newline = 'C="x\\ny"\n'
    assert parsed(header + single + double + escaped_newline + "D=end") == [
        (None, None, header, 1, False),
        ("A", "one\r\ntwo\nthree\rfour", single, 2, False),
        ("B", "left\nright", double, 7, False),
        ("C", "x\ny", escaped_newline, 9, False),
        ("D", "end", "D=end", 10, False),
    ]


@pytest.mark.parametrize(
    "bad_line",
    [
        "=no_key",
        "''=empty_key",
        "'unclosed=key",
        "TWO WORDS=value",
        "export =no_key",
        "X='unterminated",
        'X="unterminated',
        'X="closed"unexpected',
        "X='closed' more",
    ],
)
@pytest.mark.parametrize("ending", ["\n", "\r"])
def test_malformed_binding_preserves_source_and_recovers(bad_line, ending):
    before = "BEFORE=ok\r\n"
    bad = "\t" + bad_line + ending
    after = "AFTER=ok"
    assert parsed(before + bad + after) == [
        ("BEFORE", "ok", before, 1, False),
        (None, None, bad, 2, True),
        ("AFTER", "ok", after, 3, False),
    ]


def test_recovery_after_a_multiline_value_with_trailing_garbage():
    bad = '\nX="one\r\ntwo" junk\n'
    after = "AFTER=ok\n"
    last = "=broken"
    assert parsed(bad + after + last) == [
        (None, None, bad, 1, True),
        ("AFTER", "ok", after, 4, False),
        (None, None, last, 5, True),
    ]


def test_iterator_reads_from_current_stream_position():
    prefix = "OUTSIDE=ignored\n"
    stream = StringIO(prefix + "IN=first\nIN=second", newline="")
    stream.seek(len(prefix))
    bindings = parse_stream(stream)

    first = next(bindings)
    assert (first.key, first.value, first.original.string, first.original.line, first.error) == (
        "IN", "first", "IN=first\n", 1, False
    )
    second = next(bindings)
    assert (second.key, second.value, second.original.string, second.original.line, second.error) == (
        "IN", "second", "IN=second", 2, False
    )
    with pytest.raises(StopIteration):
        next(bindings)

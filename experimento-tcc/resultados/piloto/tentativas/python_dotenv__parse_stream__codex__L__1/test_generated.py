from io import StringIO

import pytest

from dotenv.parser import parse_stream


def bindings_for(source):
    return [
        (binding.key, binding.value, binding.error,
         binding.original.string, binding.original.line)
        for binding in parse_stream(StringIO(source, newline=""))
    ]


@pytest.mark.parametrize("source", ["", "\ufeff"])
def test_stream_without_content_yields_no_bindings(source):
    assert bindings_for(source) == []


@pytest.mark.parametrize("source", [" \t", "\n\r\n\r\t\u00a0"])
def test_whitespace_only_stream_preserves_original_text(source):
    assert bindings_for(source) == [(None, None, False, source, 1)]


@pytest.mark.parametrize(
    ("source", "key", "value"),
    [
        ("FLAG", "FLAG", None),
        ("FLAG \t# note\n", "FLAG", None),
        ("FLAG#note\n", "FLAG", None),
        ("EMPTY=", "EMPTY", ""),
        ("EMPTY= \t\r\n", "EMPTY", ""),
        ("EMPTY=\r", "EMPTY", ""),
        ("EMPTY=\n", "EMPTY", ""),
        ("\texport\tPORT \t= \t8080  # note\n", "PORT", "8080"),
        ("export=literal\n", "export", "literal"),
        ("exported=value\n", "exported", "value"),
        ("export\n", "export", None),
        ("'key # with = signs' = value\n", "key # with = signs", "value"),
        ("café.service-v2:port=mañana\n", "café.service-v2:port", "mañana"),
        ("A==value\n", "A", "=value"),
        ("A=#literal\n", "A", "#literal"),
        ("A=#literal with spaces\n", "A", "#literal with spaces"),
        ("A= # comment\n", "A", ""),
        ("A=\t# comment\r", "A", ""),
        ("A=\u00a0# comment\n", "A", ""),
        ("A=one#two \t# comment # remainder\n", "A", "one#two"),
        ("A=one\u00a0# comment\n", "A", "one"),
        ("A=first  second \t", "A", "first  second"),
        (r"A=before\n 'after'", "A", r"before\n 'after'"),
        ("A=''# comment\n", "A", ""),
        ('A=""\n', "A", ""),
        ("A='  # inside  '  # outside\r\n", "A", "  # inside  "),
        ('A="  # inside  "# outside\n', "A", "  # inside  "),
        ("A='one\"two'\n", "A", 'one"two'),
        ('A="one\'two"\n', "A", "one'two"),
        (r"A='it\'s\\there\n\t\"end'", "A", "it's\\there" + r'\n\t\"end'),
        (r'''A="\\\'\"\a\b\f\n\r\t\v"''', "A", "\\'\"\a\b\f\n\r\t\v"),
        (r'A="café\q\u263a\x41\0"', "A", r"café\q\u263a\x41\0"),
        (r"A='ends with \\' # comment", "A", "ends with \\"),
        (r'A="ends with \\" # comment', "A", "ends with \\"),
        (r'''A="left\\\"right"''', "A", 'left\\"right'),
    ],
)
def test_parse_single_binding(source, key, value):
    assert bindings_for(source) == [(key, value, False, source, 1)]


def test_preserves_binding_order_duplicates_and_original_line_boundaries():
    first = "# heading\r\n"
    second = "\n\t# another comment\r"
    third = "\r\n  export ITEM = first  \n"
    fourth = "ITEM=second\r\n"
    fifth = "ITEM\r"
    trailing = "\n \t"
    # The LF after the fifth binding's text would join its final CR.
    # Keep a space between them so that the trailing LF is a separate line.
    trailing = " \n\t"

    assert bindings_for(first + second + third + fourth + fifth + trailing) == [
        (None, None, False, first, 1),
        (None, None, False, second, 2),
        ("ITEM", "first", False, third, 4),
        ("ITEM", "second", False, fourth, 6),
        ("ITEM", None, False, fifth, 7),
        (None, None, False, trailing, 8),
    ]


def test_comment_at_end_of_stream():
    source = "  # comment without a newline"
    assert bindings_for(source) == [(None, None, False, source, 1)]


def test_removes_only_one_bom_at_the_start_of_the_input():
    first = "A=\ufeffvalue\r\n"
    second = "\ufeffB=next"
    assert bindings_for("\ufeff" + first + second) == [
        ("A", "\ufeffvalue", False, first, 1),
        ("\ufeffB", "next", False, second, 2),
    ]
    assert bindings_for("\ufeff\ufeffA=1") == [
        ("\ufeffA", "1", False, "\ufeffA=1", 1),
    ]


def test_multiline_values_preserve_physical_newlines_and_line_numbers():
    single = "S='one\r\ntwo\nthree\rfour'\r\n"
    double = 'D="one\\nzero\r\ntwo\\\nthree"\n'
    last = "LAST=done"

    assert bindings_for(single + double + last) == [
        ("S", "one\r\ntwo\nthree\rfour", False, single, 1),
        ("D", "one\nzero\r\ntwo\\\nthree", False, double, 5),
        ("LAST", "done", False, last, 8),
    ]


@pytest.mark.parametrize(
    "malformed",
    [
        "=missing_key",
        "export =missing_key",
        "''=empty_quoted_key",
        "'unclosed_key=value",
        "FLAG unexpected",
        "A='unclosed value",
        'A="unclosed value',
        "A='closed'junk",
        'A="closed" junk',
    ],
)
@pytest.mark.parametrize("newline", ["\n", "\r"])
def test_malformed_binding_recovers_at_the_following_line(malformed, newline):
    before = "BEFORE=ok" + newline
    invalid = " \t" + newline + "  " + malformed + newline
    after = "AFTER=ok"

    assert bindings_for(before + invalid + after) == [
        ("BEFORE", "ok", False, before, 1),
        (None, None, True, invalid, 2),
        ("AFTER", "ok", False, after, 4),
    ]


def test_recovery_after_a_multiline_value_with_invalid_trailing_text():
    invalid = 'BROKEN="first\r\nsecond" junk\n'
    assert bindings_for(invalid + "GOOD=yes\n") == [
        (None, None, True, invalid, 1),
        ("GOOD", "yes", False, "GOOD=yes\n", 3),
    ]


def test_malformed_binding_at_eof_is_yielded_once():
    source = "OK=1\nBROKEN='dangling\\"
    assert bindings_for(source) == [
        ("OK", "1", False, "OK=1\n", 1),
        (None, None, True, "BROKEN='dangling\\", 2),
    ]


def test_iterates_from_the_streams_current_position():
    stream = StringIO("IGNORED=1\nFIRST=2\nSECOND=3")
    stream.seek(len("IGNORED=1\n"))
    bindings = parse_stream(stream)

    assert iter(bindings) is bindings
    first = next(bindings)
    assert (first.key, first.value, first.error) == ("FIRST", "2", False)
    assert (first.original.string, first.original.line) == ("FIRST=2\n", 1)
    second = next(bindings)
    assert (second.key, second.value, second.error) == ("SECOND", "3", False)
    assert (second.original.string, second.original.line) == ("SECOND=3", 2)
    with pytest.raises(StopIteration):
        next(bindings)

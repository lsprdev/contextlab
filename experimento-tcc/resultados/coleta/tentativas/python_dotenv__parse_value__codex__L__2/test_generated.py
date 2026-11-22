from io import StringIO

import pytest

from dotenv.parser import Error, Reader, parse_value


@pytest.mark.parametrize("terminator", ["", "\n", "\r", "\r\n"])
def test_empty_value_leaves_line_ending_unread(terminator):
    remainder = terminator + "NEXT=value" if terminator else ""
    reader = Reader(StringIO("KEY=" + remainder))
    reader.read(len("KEY="))

    assert parse_value(reader) == ""
    assert reader.peek(len(remainder) + 1) == remainder


@pytest.mark.parametrize(
    ("source", "expected", "remainder"),
    [
        ("text", "text", ""),
        ("  alpha  beta\t  \nNEXT=1", "  alpha  beta", "\nNEXT=1"),
        ("value\rNEXT=1", "value", "\rNEXT=1"),
        ("value\r\nNEXT=1", "value", "\r\nNEXT=1"),
        (" \t\u2003\n", "", "\n"),
        ("value\u2003", "value", ""),
        ("#literal hash", "#literal hash", ""),
        ("value#tag\t # discarded # text\nNEXT=1", "value#tag", "\nNEXT=1"),
        ("value\t# discarded", "value", ""),
        ("café\u2003# discarded", "café", ""),
        (" \t# discarded\r", "", "\r"),
        ("value # discarded\u2028still discarded", "value", ""),
        ("left\vcenter\u2028right", "left\vcenter\u2028right", ""),
        ("one 'two' \"three\" = four", "one 'two' \"three\" = four", ""),
        (" 'quoted' # discarded", " 'quoted'", ""),
        (r"one\ntwo\#tag\q", r"one\ntwo\#tag\q", ""),
        ("value\\\nNEXT=1", "value\\", "\nNEXT=1"),
    ],
)
def test_unquoted_value_and_remaining_input(source, expected, remainder):
    reader = Reader(StringIO(source))

    assert parse_value(reader) == expected
    assert reader.peek(len(source) + 1) == remainder


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize(
    "body",
    ["", " \tcafé # literal\t ", "first\nsecond\r\nthird\rfourth", "left\\\nright"],
)
def test_quoted_value_preserves_literal_body_and_leaves_suffix(quote, body):
    prefix = "OTHER=1\r\nKEY="
    token = quote + body + quote
    suffix = " \t# comment\r\nNEXT=2"
    reader = Reader(StringIO(prefix + token + suffix))
    reader.read(len(prefix))
    reader.set_mark()

    assert parse_value(reader) == body
    assert reader.get_marked().string == token
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize(
    ("quote", "body", "expected"),
    [
        ("'", r"a\'b", "a'b"),
        ("'", r'a\"b', r'a\"b'),
        ("'", 'a"b', 'a"b'),
        ("'", r"\a\b\f\n\r\t\v", r"\a\b\f\n\r\t\v"),
        ('"', r'a\"b', 'a"b'),
        ('"', r"a\'b", "a'b"),
        ('"', "a'b", "a'b"),
        ('"', r"\a\b\f\n\r\t\v", "\a\b\f\n\r\t\v"),
        ('"', r"\\n\n", "\\n\n"),
        ("'", r"café\q\0\x41\u0041\U00000041\N{LATIN CAPITAL LETTER A}\$", r"café\q\0\x41\u0041\U00000041\N{LATIN CAPITAL LETTER A}\$"),
        ('"', r"café\q\0\x41\u0041\U00000041\N{LATIN CAPITAL LETTER A}\$", r"café\q\0\x41\u0041\U00000041\N{LATIN CAPITAL LETTER A}\$"),
    ],
)
def test_quoted_escape_decoding(quote, body, expected):
    reader = Reader(StringIO(quote + body + quote + "#tail"))

    assert parse_value(reader) == expected
    assert reader.peek(6) == "#tail"


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("pair_count", [1, 2])
def test_even_backslashes_allow_the_following_quote_to_close(quote, pair_count):
    token = quote + "end" + "\\" * (2 * pair_count) + quote
    suffix = "tail" + quote
    reader = Reader(StringIO(token + suffix))

    assert parse_value(reader) == "end" + "\\" * pair_count
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("quote", ["'", '"'])
def test_odd_backslashes_escape_the_following_quote(quote):
    token = quote + "left" + "\\" * 3 + quote + "right" + quote
    reader = Reader(StringIO(token + "\n"))

    assert parse_value(reader) == "left\\" + quote + "right"
    assert reader.peek(2) == "\n"


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("body", ["", "unterminated\r\nvalue", "ends in a backslash\\"])
def test_unclosed_quote_raises_parser_error_without_consuming_input(quote, body):
    source = quote + body
    reader = Reader(StringIO(source))

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.peek(len(source) + 1) == source


@pytest.mark.parametrize("quote", ["'", '"'])
def test_escaped_final_quote_cannot_close_value(quote):
    source = quote + "body\\" + quote
    reader = Reader(StringIO(source))

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.peek(len(source) + 1) == source

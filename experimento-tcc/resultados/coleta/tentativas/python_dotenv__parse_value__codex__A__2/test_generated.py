from io import StringIO

import pytest

from dotenv.parser import Error, Reader, parse_value


@pytest.mark.parametrize("remaining", ["", "\nNEXT=1", "\rNEXT=1", "\r\nNEXT=1"])
def test_empty_value_leaves_line_ending_unread(remaining):
    reader = Reader(StringIO("KEY=" + remaining))
    assert reader.read(4) == "KEY="
    reader.set_mark()

    assert parse_value(reader) == ""
    assert reader.get_marked().string == ""
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize("ending", ["", "\nNEXT=1", "\rNEXT=1", "\r\nNEXT=1"])
def test_unquoted_value_consumes_comment_and_padding_but_leaves_line_ending(ending):
    raw = "café  # comment\t "
    reader = Reader(StringIO(raw + ending))

    assert parse_value(reader) == "café"
    assert reader.get_marked().string == raw
    assert reader.peek(len(ending) + 1) == ending


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("#literal", "#literal"),
        ("a#b # comment", "a#b"),
        ("a\t# comment", "a"),
        ("a\u00a0# comment", "a"),
        (" \t# comment", ""),
        (" \t  ", ""),
        (" \talpha  beta\t\u2003", " \talpha  beta"),
        (" \"literal\"", " \"literal\""),
        ("a='b'\"c\"", "a='b'\"c\""),
        (r"C:\new\temp\q", r"C:\new\temp\q"),
        ("path\\ # comment", "path\\"),
    ],
)
def test_unquoted_value_text(raw, expected):
    reader = Reader(StringIO(raw))

    assert parse_value(reader) == expected
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("body", ["", " \tcafé # literal  ", "a\r\nb\rc\nd", "a\\\nb"])
def test_quoted_value_preserves_text_and_stops_at_closing_quote(quote, body):
    raw = quote + body + quote
    suffix = " \t# comment\r\nNEXT=1"
    reader = Reader(StringIO("KEY=" + raw + suffix))
    reader.read(4)
    reader.set_mark()

    assert parse_value(reader) == body
    assert reader.get_marked().string == raw
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("quote", ["'", '"'])
def test_quoted_value_stops_before_adjacent_quoted_text(quote):
    suffix = quote + "second" + quote
    reader = Reader(StringIO(quote + "first" + quote + suffix))

    assert parse_value(reader) == "first"
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize(
    ("escape", "decoded"),
    [
        (r"\\", "\\"),
        (r"\'", "'"),
        (r'\"', '"'),
        (r"\a", "\a"),
        (r"\b", "\b"),
        (r"\f", "\f"),
        (r"\n", "\n"),
        (r"\r", "\r"),
        (r"\t", "\t"),
        (r"\v", "\v"),
    ],
)
def test_double_quoted_supported_escapes(escape, decoded):
    reader = Reader(StringIO('"é' + escape + '雪"'))

    assert parse_value(reader) == "é" + decoded + "雪"
    assert not reader.has_next()


@pytest.mark.parametrize(
    ("quote", "body", "expected"),
    [
        ("'", r"it\'s", "it's"),
        ("'", r"a\\b", "a\\b"),
        ("'", r'\"\a\b\f\n\r\t\v', r'\"\a\b\f\n\r\t\v'),
        ("'", 'a"b', 'a"b'),
        ('"', "a'b", "a'b"),
        ('"', r"\q\x41\u2603\101\#", r"\q\x41\u2603\101\#"),
        ("'", r"\q\x41\u2603\101\#", r"\q\x41\u2603\101\#"),
        ('"', r"\\n", r"\n"),
    ],
)
def test_quote_specific_escape_rules(quote, body, expected):
    reader = Reader(StringIO(quote + body + quote))

    assert parse_value(reader) == expected
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("backslashes", [1, 2, 3, 4])
def test_backslashes_determine_whether_quote_ends_value(quote, backslashes):
    raw = quote + "a" + "\\" * backslashes + quote
    expected = "a" + "\\" * (backslashes // 2)
    if backslashes % 2:
        raw += "b" + quote
        expected += quote + "b"
    suffix = " # suffix"
    reader = Reader(StringIO(raw + suffix))

    assert parse_value(reader) == expected
    assert reader.get_marked().string == raw
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("body", ["", "unfinished\nsecond line", "trailing\\", None])
def test_unterminated_quote_raises_without_consuming_input(quote, body):
    raw = quote + ("escaped closing quote\\" + quote if body is None else body)
    reader = Reader(StringIO(raw))

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.peek(len(raw) + 1) == raw


@pytest.mark.parametrize("quote", ["'", '"'])
def test_multiline_value_advances_reader_by_physical_line_endings(quote):
    body = "one\r\ntwo\rthree\nfour" + r"\n"
    reader = Reader(StringIO(quote + body + quote + "\r\nnext"))
    expected = body if quote == "'" else "one\r\ntwo\rthree\nfour\n"

    assert parse_value(reader) == expected
    reader.set_mark()
    assert reader.get_marked().line == 4
    assert reader.read(2) == "\r\n"
    reader.set_mark()
    assert parse_value(reader) == "next"
    assert reader.get_marked().line == 5

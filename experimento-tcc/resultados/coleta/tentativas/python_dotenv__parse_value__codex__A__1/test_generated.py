from io import StringIO

import pytest

from dotenv.parser import Error, Reader, parse_value


@pytest.mark.parametrize("suffix", ["", "\nNEXT=value", "\rNEXT=value", "\r\nNEXT=value"])
def test_empty_value_leaves_line_ending_unread(suffix):
    reader = Reader(StringIO("KEY=" + suffix))
    reader.read(len("KEY="))

    assert parse_value(reader) == ""
    assert reader.peek(len(suffix) + 1) == suffix
    assert reader.has_next() is bool(suffix)


@pytest.mark.parametrize("quote", ["'", '"'], ids=["single", "double"])
@pytest.mark.parametrize(
    "body",
    ["", " \t café 雪 # literal ${HOME} \t ", "first\r\nsecond\nthird\rfourth", "first" + "\\" + "\nsecond"],
    ids=["empty", "literal-content", "multiline", "backslash-before-newline"],
)
def test_quoted_value_preserves_literal_content_and_stops_at_closing_quote(quote, body):
    token = quote + body + quote
    suffix = " \t# another " + quote + "\r\nNEXT=1"
    reader = Reader(StringIO("KEY=" + token + suffix))
    reader.read(len("KEY="))

    assert parse_value(reader) == body
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("quote", ["'", '"'], ids=["single", "double"])
def test_quoted_value_distinguishes_escaped_quote_from_escaped_backslash(quote):
    backslash = "\\"
    token = quote + "left" + backslash * 3 + quote + "right" + backslash * 2 + quote
    reader = Reader(StringIO(token + "tail" + quote))

    assert parse_value(reader) == "left" + backslash + quote + "right" + backslash
    assert reader.peek(6) == "tail" + quote


def test_double_quoted_value_decodes_supported_escapes():
    body = r"\a|\b|\f|\n|\r|\t|\v|\\|\'|\" + '"'
    reader = Reader(StringIO('"' + body + '"'))

    assert parse_value(reader) == "\a|\b|\f|\n|\r|\t|\v|\\|'|\""
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'], ids=["single", "double"])
def test_quoted_value_leaves_unsupported_escapes_literal(quote):
    body = r"\q\0\123\x41\u0042\U00000043\N{LATIN CAPITAL LETTER D}\/\#"
    reader = Reader(StringIO(quote + body + quote))

    assert parse_value(reader) == body
    assert not reader.has_next()


def test_single_quoted_value_preserves_double_quote_only_escapes():
    body = r'\"\a\b\f\n\r\t\v'
    reader = Reader(StringIO("'" + body + "'"))

    assert parse_value(reader) == body
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'], ids=["single", "double"])
@pytest.mark.parametrize(
    "body",
    ["", "unterminated\nNEXT=value", "dangling" + "\\", None],
    ids=["opening-only", "missing-close-after-newline", "dangling-backslash", "escaped-final-quote"],
)
def test_unterminated_quoted_value_raises_without_consuming_input(quote, body):
    if body is None:
        body = "escaped" + "\\" + quote
    source = quote + body
    reader = Reader(StringIO(source))

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.peek(len(source) + 1) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("plain value \t\u2003", "plain value"),
        (" \t keep leading spaces \t", " \t keep leading spaces"),
        (" \t\u2003", ""),
        ("#literal", "#literal"),
        ("one#two#three", "one#two#three"),
        ("one#two \t# discard # all", "one#two"),
        ("café\u2003# comment", "café"),
        ("value\v# comment", "value"),
        (" \t# comment only", ""),
        ("value #", "value"),
        ("value#", "value#"),
        (r'''x='one' "two"\n\t\#${HOME}''', r'''x='one' "two"\n\t\#${HOME}'''),
        (" \t'quoted' # comment", " \t'quoted'"),
    ],
)
def test_unquoted_value_trims_trailing_whitespace_and_handles_hashes(source, expected):
    suffix = "\r\nNEXT=value"
    reader = Reader(StringIO(source + suffix))

    assert parse_value(reader) == expected
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("ending", ["\n", "\r", "\r\n"], ids=["lf", "cr", "crlf"])
def test_unquoted_value_stops_at_line_ending_even_after_a_backslash(ending):
    first_value = "first" + "\\"
    reader = Reader(StringIO(first_value + ending + "second"))

    assert parse_value(reader) == first_value
    assert reader.read(len(ending)) == ending
    assert parse_value(reader) == "second"
    assert not reader.has_next()

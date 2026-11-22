from io import StringIO

import pytest

from dotenv.parser import Error, Original, Reader, parse_value


@pytest.mark.parametrize("prefix", ["", "KEY="], ids=["start", "after-equals"])
@pytest.mark.parametrize(
    ("consumed", "remaining", "expected"),
    [
        pytest.param("", "", "", id="eof"),
        pytest.param("", "\nnext", "", id="empty-before-lf"),
        pytest.param("", "\rnext", "", id="empty-before-cr"),
        pytest.param("", "\r\nnext", "", id="empty-before-crlf"),
        pytest.param("''", " # comment\n", "", id="empty-single-quoted"),
        pytest.param('""', "# comment\r\n", "", id="empty-double-quoted"),
        pytest.param("'  café # literal  '", " trailing", "  café # literal  ", id="single-quoted-whitespace-and-hash"),
        pytest.param('"\t雪 # literal  "', "\nnext", "\t雪 # literal  ", id="double-quoted-whitespace-and-hash"),
        pytest.param("'a\"b'", "'later'", 'a"b', id="double-quote-inside-single-quotes"),
        pytest.param('"a\'b"', '"later"', "a'b", id="single-quote-inside-double-quotes"),
        pytest.param(r"""'can\'t \\ \" \n \t \a \b \f \r \v'""", "", r"""can't \ \" \n \t \a \b \f \r \v""", id="single-quote-escapes"),
        pytest.param(r'''"\\\'\"\a\b\f\n\r\t\v"''', "", "\\'\"\a\b\f\n\r\t\v", id="double-quote-escapes"),
        pytest.param(r"""'tail\\'""", " 'later'", "tail\\", id="single-quoted-final-backslash"),
        pytest.param(r'''"tail\\"''', ' "later"', "tail\\", id="double-quoted-final-backslash"),
        pytest.param(r'"\q \x41 \u0041 \101 \0 \/"', "", r'\q \x41 \u0041 \101 \0 \/', id="unsupported-double-quote-escapes"),
        pytest.param("plain", "", "plain", id="unquoted-through-eof"),
        pytest.param("one\ttwo \t\u00a0", "\nnext", "one\ttwo", id="unquoted-trailing-whitespace"),
        pytest.param("\t  ", "\rnext", "", id="unquoted-only-whitespace"),
        pytest.param("one#two\t # comment # more", "\r\nnext", "one#two", id="unquoted-inline-comment"),
        pytest.param("café\u00a0# comment", "", "café", id="unquoted-unicode-comment-separator"),
        pytest.param("# literal", "\rnext", "# literal", id="unquoted-leading-hash"),
        pytest.param(" \t# comment", "\nnext", "", id="unquoted-only-comment"),
        pytest.param(r'''  "text" 'more' \n \\''', "\nnext", r'''  "text" 'more' \n \\''', id="unquoted-leading-whitespace-and-literal-escapes"),
    ],
)
def test_parse_value_returns_value_and_consumes_source(prefix, consumed, remaining, expected):
    reader = Reader(StringIO(prefix + consumed + remaining))
    reader.read(len(prefix))
    reader.set_mark()

    assert parse_value(reader) == expected
    assert reader.get_marked() == Original(consumed, 1)
    assert reader.read(len(remaining)) == remaining
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'], ids=["single-quoted", "double-quoted"])
def test_parse_value_preserves_physical_line_breaks_in_quotes(quote):
    prefix = "previous\r\n"
    body = "café\r\nβ\\\nγ\rδ"
    value_source = quote + body + quote
    remaining = "\r\nNEXT=value"
    reader = Reader(StringIO(prefix + value_source + remaining))
    reader.read(len(prefix))
    reader.set_mark()

    assert parse_value(reader) == body
    assert reader.get_marked() == Original(value_source, 2)
    reader.set_mark()
    assert reader.get_marked() == Original("", 5)
    assert reader.read(len(remaining)) == remaining
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'], ids=["single-quoted", "double-quoted"])
@pytest.mark.parametrize(
    "body",
    ["", "unfinished\r\ncontinued", "dangling\\"],
    ids=["opening-quote-only", "unterminated-multiline", "trailing-backslash"],
)
def test_parse_value_rejects_unterminated_quotes_without_consuming_input(quote, body):
    source = quote + body
    reader = Reader(StringIO(source))
    reader.set_mark()

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked() == Original("", 1)
    assert reader.read(len(source)) == source
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'], ids=["single-quoted", "double-quoted"])
def test_parse_value_rejects_escaped_quote_at_eof(quote):
    source = quote + "escaped closer\\" + quote
    reader = Reader(StringIO(source))
    reader.set_mark()

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked() == Original("", 1)
    assert reader.read(len(source)) == source

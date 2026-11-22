from io import StringIO

import pytest

from dotenv.parser import Error, Reader, parse_value


@pytest.mark.parametrize("source", ["", "\nnext", "\rnext", "\r\nnext"])
def test_empty_value_leaves_reader_in_place(source):
    reader = Reader(StringIO(source))

    assert parse_value(reader) == ""
    assert reader.get_marked().string == ""
    assert reader.peek(len(source) + 1) == source
    assert reader.has_next() is bool(source)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("plain", "plain"),
        ("#literal", "#literal"),
        ("left#middle # comment # more", "left#middle"),
        ("left\t# comment", "left"),
        ("left\u00a0# comment", "left"),
        (" \t# comment", ""),
        ("left\\ # comment", "left\\"),
        ("  two\twords=ok\u00a0 \t", "  two\twords=ok"),
        (" \t\u00a0", ""),
        ('  "quoted-looking" # comment', '  "quoted-looking"'),
        ("prefix'one'\"two\"", "prefix'one'\"two\""),
        (r"${NAME}\n\t\#literal", r"${NAME}\n\t\#literal"),
        ("café\u2028雪", "café\u2028雪"),
    ],
)
def test_unquoted_value_at_end_of_input(token, expected):
    reader = Reader(StringIO(token))

    assert parse_value(reader) == expected
    assert reader.get_marked().string == token
    assert not reader.has_next()


@pytest.mark.parametrize("newline", ["\n", "\r", "\r\n"])
def test_unquoted_value_consumes_inline_comment_and_leaves_line_ending(newline):
    token = "value \t# comment"
    remainder = newline + "NEXT=other"
    reader = Reader(StringIO(token + remainder))

    assert parse_value(reader) == "value"
    assert reader.get_marked().string == token
    assert reader.peek(len(remainder) + 1) == remainder


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("''", ""),
        ('""', ""),
        ("'  café \"tea\" # literal \t '", '  café "tea" # literal \t '),
        ('"  雪 \'tea\' # literal \t "', "  雪 'tea' # literal \t "),
        (r'''"\\ \' \" \a \b \f \n \r \t \v"''', "\\ ' \" \a \b \f \n \r \t \v"),
        (r''' '\\ \' \" \a \b \f \n \r \t \v' '''.strip(), "\\ ' " + r'''\" \a \b \f \n \r \t \v'''),
        (r'"\q \0 \101 \x41 \u0041 \U00000041 \N{LATIN CAPITAL LETTER A} \/"',
         r'\q \0 \101 \x41 \u0041 \U00000041 \N{LATIN CAPITAL LETTER A} \/'),
        (r"'\q \0 \101 \x41 \u0041 \/'", r"\q \0 \101 \x41 \u0041 \/"),
        (r'"\\n\\t"', r'\n\t'),
        (r"'\\n\\t'", r"\n\t"),
    ],
)
def test_quoted_value_decodes_its_escapes_and_leaves_suffix(token, expected):
    suffix = " \t# comment\r\nNEXT=other"
    reader = Reader(StringIO(token + suffix))

    assert parse_value(reader) == expected
    assert reader.get_marked().string == token
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("pairs", [0, 1, 2, 3])
def test_backslash_parity_determines_which_quote_closes_value(quote, pairs):
    escaped_quote = "\\" * (2 * pairs + 1) + quote
    before_closing_quote = "\\" * (2 * pairs)
    token = quote + "a" + escaped_quote + "b" + before_closing_quote + quote
    suffix = quote + "later" + quote
    reader = Reader(StringIO(token + suffix))
    backslashes = "\\" * pairs

    assert parse_value(reader) == "a" + backslashes + quote + "b" + backslashes
    assert reader.get_marked().string == token
    assert reader.peek(len(suffix) + 1) == suffix
    assert parse_value(reader) == "later"
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'])
def test_multiline_quote_starts_at_current_position(quote):
    prefix = "previous\r\nKEY="
    body = "first\\\nsecond\r\nthird\rfourth"
    token = quote + body + quote
    suffix = "tail"
    reader = Reader(StringIO(prefix + token + suffix))
    reader.read(len(prefix))
    reader.set_mark()

    assert parse_value(reader) == body
    assert reader.get_marked().string == token
    assert reader.get_marked().line == 2
    assert reader.peek(len(suffix) + 1) == suffix

    reader.set_mark()
    assert reader.get_marked().line == 5
    assert parse_value(reader) == suffix
    assert not reader.has_next()


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("body", ["", "unfinished\nnext", "trailing\\", "escaped\\{quote}"])
def test_unterminated_quote_raises_without_consuming_input(quote, body):
    source = quote + body.format(quote=quote)
    reader = Reader(StringIO(source))

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked().string == ""
    assert reader.peek(len(source) + 1) == source

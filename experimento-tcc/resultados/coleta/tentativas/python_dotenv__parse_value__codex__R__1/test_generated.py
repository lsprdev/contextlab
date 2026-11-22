from io import StringIO

import pytest

from dotenv.parser import Error, Reader, parse_value


@pytest.mark.parametrize('remaining', ['', '\nNEXT=1', '\rNEXT=1', '\r\nNEXT=1'])
def test_empty_value_leaves_line_ending_unread(remaining):
    reader = Reader(StringIO('KEY=' + remaining))
    reader.read(4)
    reader.set_mark()

    assert parse_value(reader) == ''
    assert reader.get_marked().string == ''
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('plain', 'plain'),
        ('alpha beta\tgamma', 'alpha beta\tgamma'),
        ('  leading space\t ', '  leading space'),
        ('plain\t\u2003 ', 'plain'),
        ('\t \u2003', ''),
        ('#literal', '#literal'),
        ('#literal text # comment', '#literal text'),
        ('token#fragment\t # discarded # also discarded', 'token#fragment'),
        ('token\u2003# comment', 'token'),
        (' \t# comment only', ''),
        ('token #', 'token'),
        (r'C:\new\folder\name', r'C:\new\folder\name'),
        ('ab\'cd"ef=${NAME}', 'ab\'cd"ef=${NAME}'),
        (' "quoted-looking" # comment', ' "quoted-looking"'),
        ('café 🌱#tag', 'café 🌱#tag'),
    ],
)
@pytest.mark.parametrize('remaining', ['', '\nNEXT=1', '\rNEXT=1', '\r\nNEXT=1'])
def test_unquoted_value_stops_at_line_ending(source, expected, remaining):
    reader = Reader(StringIO('KEY=' + source + remaining))
    reader.read(4)
    reader.set_mark()

    assert parse_value(reader) == expected
    assert reader.get_marked().string == source
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize('quote', ["'", '"'])
@pytest.mark.parametrize('body', ['', '  café 🌱 # kept\t ', 'first\r\nsecond\nthird\rfourth'])
@pytest.mark.parametrize('remaining', ['', ' \t# outside\r\nNEXT=1', 'tail'])
def test_quoted_value_preserves_content_and_stops_at_closing_quote(quote, body, remaining):
    source = quote + body + quote
    reader = Reader(StringIO('KEY=' + source + remaining))
    reader.read(4)
    reader.set_mark()

    assert parse_value(reader) == body
    assert reader.get_marked().string == source
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize(
    ('quote', 'body', 'expected'),
    [
        ("'", 'a"b', 'a"b'),
        ('"', "a'b", "a'b"),
        ("'", r"a\'b", "a'b"),
        ('"', r'a\"b', 'a"b'),
        ("'", r'\"', r'\"'),
        ('"', r"\'", "'"),
        ("'", r'\a\b\f\n\r\t\v', r'\a\b\f\n\r\t\v'),
        ('"', r'\a\b\f\n\r\t\v', '\a\b\f\n\r\t\v'),
    ],
)
def test_quote_specific_escapes(quote, body, expected):
    reader = Reader(StringIO(quote + body + quote + 'tail'))

    assert parse_value(reader) == expected
    assert reader.peek(5) == 'tail'


@pytest.mark.parametrize('quote', ["'", '"'])
@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        (r'café\q\x41\u0041\101\$🌱', r'café\q\x41\u0041\101\$🌱'),
        (r'left\\right', 'left\\right'),
        (r'ends in \\', 'ends in \\'),
        (r'\\n', r'\n'),
        ('before\\\nafter', 'before\\\nafter'),
    ],
)
def test_backslash_pairs_and_unrecognized_escapes(quote, body, expected):
    reader = Reader(StringIO(quote + body + quote + ' # suffix'))

    assert parse_value(reader) == expected
    assert reader.peek(10) == ' # suffix'


@pytest.mark.parametrize('quote', ["'", '"'])
def test_odd_backslash_run_escapes_embedded_delimiter(quote):
    body = 'before' + '\\' * 3 + quote + 'after'
    reader = Reader(StringIO(quote + body + quote + '\n'))

    assert parse_value(reader) == 'before\\' + quote + 'after'
    assert reader.peek(2) == '\n'


@pytest.mark.parametrize('quote', ["'", '"'])
def test_parse_value_can_read_adjacent_quoted_values(quote):
    reader = Reader(StringIO(quote + 'first' + quote + quote + 'second' + quote))

    assert parse_value(reader) == 'first'
    assert parse_value(reader) == 'second'
    assert not reader.has_next()


@pytest.mark.parametrize('quote', ["'", '"'])
@pytest.mark.parametrize('body', ['', 'unfinished', 'unfinished\\', 'first\nsecond', 'unfinished\\{quote}'])
def test_unterminated_quoted_value_raises_without_consuming_input(quote, body):
    source = quote + body.format(quote=quote)
    reader = Reader(StringIO('KEY=' + source))
    reader.read(4)
    reader.set_mark()

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked().string == ''
    assert reader.peek(len(source) + 1) == source

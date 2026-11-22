from io import StringIO

import pytest

from dotenv.parser import Error, Original, Reader, parse_value


@pytest.mark.parametrize(
    ('consumed', 'remaining', 'expected', 'line_breaks'),
    [
        pytest.param('', '', '', 0, id='empty-at-eof'),
        pytest.param('', '\nNEXT=1', '', 0, id='empty-before-lf'),
        pytest.param('', '\rNEXT=1', '', 0, id='empty-before-cr'),
        pytest.param('', '\r\nNEXT=1', '', 0, id='empty-before-crlf'),
        pytest.param("''", ' # comment\r\n', '', 0, id='empty-single-quoted'),
        pytest.param('""', '\t# comment\n', '', 0, id='empty-double-quoted'),
        pytest.param('plain', '', 'plain', 0, id='unquoted-at-eof'),
        pytest.param(' a b\t  ', '\nNEXT=1', ' a b', 0, id='unquoted-trailing-space'),
        pytest.param('\t \u00a0', '\rNEXT=1', '', 0, id='whitespace-only'),
        pytest.param('abc\t # comment # more', '\r\nNEXT=1', 'abc', 0, id='inline-comment'),
        pytest.param('abc\u00a0# comment', '\n', 'abc', 0, id='unicode-space-before-comment'),
        pytest.param(' # comment', '', '', 0, id='comment-after-leading-space'),
        pytest.param('#literal', '\r\n', '#literal', 0, id='leading-hash-is-literal'),
        pytest.param('one#two # three', '\n', 'one#two', 0, id='attached-and-comment-hashes'),
        pytest.param(' #', '\n', '', 0, id='empty-comment'),
        pytest.param(r'one\n\t\#two=C:\tmp', '\r', r'one\n\t\#two=C:\tmp', 0, id='unquoted-backslashes'),
        pytest.param(" 'abc'\t", '\n', " 'abc'", 0, id='quote-after-space-is-literal'),
        pytest.param('a"b\'c', '\n', 'a"b\'c', 0, id='quotes-inside-unquoted-value'),
        pytest.param('a\vb\fc\u2028d', '\n', 'a\vb\fc\u2028d', 0, id='unquoted-non-cr-lf-separators'),
        pytest.param("'  café # 雪  '", 'tail\n', '  café # 雪  ', 0, id='single-quoted-literal-content'),
        pytest.param('"  café # 雪  "', 'tail\n', '  café # 雪  ', 0, id='double-quoted-literal-content'),
        pytest.param("'a\"b'", "'second'", 'a"b', 0, id='single-quoted-stops-at-first-closing-quote'),
        pytest.param('"a\'b"', '"second"', "a'b", 0, id='double-quoted-stops-at-first-closing-quote'),
        pytest.param("'a\nb\r\nc\rd'", '\r\nNEXT=1', 'a\nb\r\nc\rd', 3, id='single-quoted-multiline'),
        pytest.param('"a\nb\r\nc\rd"', '\nNEXT=1', 'a\nb\r\nc\rd', 3, id='double-quoted-multiline'),
    ],
)
def test_parse_value_returns_text_and_advances_to_end_of_value(
    consumed, remaining, expected, line_breaks
):
    prefix = 'pré\r\nKEY='
    reader = Reader(StringIO(prefix + consumed + remaining))
    reader.read(len(prefix))
    reader.set_mark()

    assert parse_value(reader) == expected
    assert reader.get_marked() == Original(consumed, 2)
    assert reader.position.chars == len(prefix + consumed)
    assert reader.position.line == 2 + line_breaks
    assert reader.peek(len(remaining) + 1) == remaining
    assert reader.has_next() == bool(remaining)


@pytest.mark.parametrize(
    ('quote', 'body', 'expected'),
    [
        pytest.param('"', r'\a\b\f\n\r\t\v', '\a\b\f\n\r\t\v', id='double-quoted-control-escapes'),
        pytest.param("'", r'\a\b\f\n\r\t\v', r'\a\b\f\n\r\t\v', id='single-quoted-control-escapes-stay-literal'),
        pytest.param('"', r'''\"\'\\''', '\"\'\\', id='double-quoted-quote-and-backslash-escapes'),
        pytest.param("'", r'''\'\"\\''', "'" + r'\"' + '\\', id='single-quoted-quote-and-backslash-escapes'),
        pytest.param('"', r'café\n雪\t🙂', 'café\n雪\t🙂', id='double-quoted-escapes-with-unicode'),
        pytest.param("'", r"café\'雪", "café'雪", id='single-quoted-escapes-with-unicode'),
        pytest.param('"', r'\x41\u0042\U00000043\101\0\N{SPACE}\q\e\/', r'\x41\u0042\U00000043\101\0\N{SPACE}\q\e\/', id='double-quoted-unsupported-escapes'),
        pytest.param("'", r'\x41\u0042\101\q', r'\x41\u0042\101\q', id='single-quoted-unsupported-escapes'),
        pytest.param('"', r'\\n\\t', r'\n\t', id='decoded-backslashes-are-not-decoded-again'),
    ],
)
def test_parse_value_decodes_only_supported_escapes(quote, body, expected):
    source = quote + body + quote
    reader = Reader(StringIO(source))

    assert parse_value(reader) == expected
    assert reader.get_marked() == Original(source, 1)
    assert reader.position.line == 1
    assert not reader.has_next()


@pytest.mark.parametrize('quote', ["'", '"'], ids=['single', 'double'])
@pytest.mark.parametrize(
    ('backslash_count', 'ends_at_first_quote'),
    [(1, False), (2, True), (3, False), (4, True)],
)
def test_parse_value_respects_backslash_parity_before_quote(
    quote, backslash_count, ends_at_first_quote
):
    first_part = quote + 'left' + '\\' * backslash_count + quote
    second_part = 'right' + quote
    reader = Reader(StringIO(first_part + second_part + '\n'))
    expected = 'left' + '\\' * (backslash_count // 2)

    if ends_at_first_quote:
        assert parse_value(reader) == expected
        assert reader.peek(len(second_part) + 1) == second_part + '\n'
    else:
        assert parse_value(reader) == expected + quote + 'right'
        assert reader.peek(len(second_part) + 1) == '\n'


@pytest.mark.parametrize('quote', ["'", '"'], ids=['single', 'double'])
@pytest.mark.parametrize('newline', ['\n', '\r', '\r\n'], ids=['lf', 'cr', 'crlf'])
def test_parse_value_preserves_backslash_before_physical_newline(quote, newline):
    body = 'left\\' + newline + 'right'
    source = quote + body + quote
    reader = Reader(StringIO(source + '\n'))

    assert parse_value(reader) == body
    assert reader.get_marked() == Original(source, 1)
    assert reader.position.line == 2
    assert reader.peek(2) == '\n'


@pytest.mark.parametrize('quote', ["'", '"'], ids=['single', 'double'])
@pytest.mark.parametrize(
    'body',
    ['', 'unterminated', 'dangling\\', 'escaped\\{quote}', 'first\r\nsecond'],
    ids=['opening-quote-only', 'missing-closer', 'dangling-backslash', 'escaped-closer', 'multiline'],
)
def test_parse_value_raises_for_unterminated_quote_without_consuming_input(quote, body):
    source = quote + body.format(quote=quote)
    reader = Reader(StringIO('K=' + source))
    reader.read(2)
    reader.set_mark()

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked() == Original('', 1)
    assert reader.position.chars == 2
    assert reader.position.line == 1
    assert reader.peek(len(source)) == source

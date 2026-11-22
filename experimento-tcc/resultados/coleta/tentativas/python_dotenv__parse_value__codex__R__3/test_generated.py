from io import StringIO

import pytest

from dotenv.parser import Error, Reader, parse_value


@pytest.mark.parametrize("remaining", ["", "\nNEXT=x", "\rNEXT=x", "\r\nNEXT=x"])
def test_empty_value_leaves_reader_at_end_of_line(remaining):
    reader = Reader(StringIO("KEY=" + remaining))
    reader.read(len("KEY="))
    reader.set_mark()

    assert parse_value(reader) == ""
    assert reader.get_marked().string == ""
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("plain text", "plain text"),
        ("  café 雪  \t", "  café 雪"),
        (" \t", ""),
        ("#literal", "#literal"),
        ("foo#bar \t# first comment # second comment", "foo#bar"),
        ("\t# comment", ""),
        ("foo\u00a0# comment", "foo"),
        ("foo\u2003", "foo"),
        ("foo \\#bar", "foo \\#bar"),
        (r"C:\new\test\x41", r"C:\new\test\x41"),
        ("  'quoted'", "  'quoted'"),
        ('pre"quoted"=suffix', 'pre"quoted"=suffix'),
        ("foo\vbar", "foo\vbar"),
    ],
)
@pytest.mark.parametrize("remaining", ["", "\nNEXT=x", "\rNEXT=x", "\r\nNEXT=x"])
def test_unquoted_value_consumes_only_the_current_line(source, expected, remaining):
    reader = Reader(StringIO(source + remaining))
    reader.set_mark()

    assert parse_value(reader) == expected
    assert reader.get_marked().string == source
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("body", ["", " \t café 雪 # literal \t "])
def test_quoted_value_preserves_content_and_stops_at_closing_quote(quote, body):
    source = quote + body + quote
    remaining = quote + "next" + quote + " \t# outside\r\nNEXT=x"
    reader = Reader(StringIO("KEY=" + source + remaining))
    reader.read(len("KEY="))
    reader.set_mark()

    assert parse_value(reader) == body
    assert reader.get_marked().string == source
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize(
    ("quote", "body", "expected"),
    [
        ("'", r"a\'b", "a'b"),
        ("'", r"a\\", "a\\"),
        ("'", r"a\\\'b", "a\\'b"),
        ("'", r'''a"b\"\a\b\f\n\r\t\v\x41\101\u0041\q''',
              r'''a"b\"\a\b\f\n\r\t\v\x41\101\u0041\q'''),
        ('"', r'a\"b', 'a"b'),
        ('"', r"a\\", "a\\"),
        ('"', r'a\\\"b', 'a\\"b'),
        ('"', r"a'b\'c", "a'b'c"),
        ('"', r"\a\b\f\n\r\t\v", "\a\b\f\n\r\t\v"),
        ('"', r"\\n", r"\n"),
        ('"', r"\x41\101\u0041\U00000041\N{LATIN CAPITAL LETTER A}\q",
              r"\x41\101\u0041\U00000041\N{LATIN CAPITAL LETTER A}\q"),
    ],
)
def test_quoted_value_decodes_only_supported_escapes(quote, body, expected):
    source = quote + body + quote
    remaining = " # outside\n"
    reader = Reader(StringIO(source + remaining))

    assert parse_value(reader) == expected
    assert reader.get_marked().string == source
    assert reader.peek(len(remaining) + 1) == remaining


@pytest.mark.parametrize("quote", ["'", '"'])
def test_quoted_value_preserves_multiline_content_and_advances_line(quote):
    prefix = "PREVIOUS=x\r\nKEY="
    body = "one\r\ntwo\\\nthree\rfour"
    source = quote + body + quote
    remaining = "\r\nNEXT=x"
    reader = Reader(StringIO(prefix + source + remaining))
    reader.read(len(prefix))
    reader.set_mark()

    assert parse_value(reader) == body
    original = reader.get_marked()
    assert original.string == source
    assert original.line == 2
    assert reader.peek(len(remaining) + 1) == remaining
    reader.set_mark()
    assert reader.get_marked().line == 5


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("body", ["", "unterminated\nNEXT=x", "trailing\\", "escaped\\{quote}"])
def test_unterminated_quoted_value_raises_without_consuming_input(quote, body):
    source = quote + body.format(quote=quote)
    reader = Reader(StringIO("KEY=" + source))
    reader.read(len("KEY="))
    reader.set_mark()

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked().string == ""
    assert reader.peek(len(source) + 1) == source

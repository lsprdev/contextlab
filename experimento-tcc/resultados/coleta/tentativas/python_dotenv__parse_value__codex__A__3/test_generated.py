from io import StringIO

import pytest

from dotenv.parser import Error, Reader, parse_value


@pytest.fixture
def value_reader():
    def make_reader(source):
        prefix = "PREVIOUS=ok\r\nNAME="
        reader = Reader(StringIO(prefix + source))
        reader.read(len(prefix))
        reader.set_mark()
        return reader

    return make_reader


@pytest.mark.parametrize("suffix", ["", "\nNEXT=x", "\rNEXT=x", "\r\nNEXT=x"])
def test_empty_value_leaves_reader_at_value_start(value_reader, suffix):
    reader = value_reader(suffix)

    assert parse_value(reader) == ""
    assert reader.get_marked().string == ""
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize(
    ("source", "suffix", "expected"),
    [
        ("plain", "", "plain"),
        ("  first\t second  \t", "\nNEXT=x", "  first\t second"),
        (" \t\u2003", "\r\nNEXT=x", ""),
        ("#literal", "\rNEXT=x", "#literal"),
        (" \t# comment", "\nNEXT=x", ""),
        ("one#two\t# three # four", "\r\nNEXT=x", "one#two"),
        ("café\u2003# comentário", "\rNEXT=x", "café"),
        ("a='single'\"double\" " + r"\n\t\#", "", "a='single'\"double\" " + r"\n\t\#"),
        ("one\v two\u2028three\u2003", "\nNEXT=x", "one\v two\u2028three"),
    ],
)
def test_unquoted_value_consumes_only_its_line(value_reader, source, suffix, expected):
    reader = value_reader(source + suffix)

    assert parse_value(reader) == expected
    assert reader.get_marked().string == source
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize(
    ("body", "suffix"),
    [
        ("", ""),
        (" \t café 😀 # inside \t ", " \t# outside\nNEXT=x"),
        ("${OTHER}=value", "# outside\rNEXT=x"),
    ],
)
def test_quoted_value_preserves_contents_and_stops_at_closing_quote(
    value_reader, quote, body, suffix
):
    source = quote + body + quote
    reader = value_reader(source + suffix)

    assert parse_value(reader) == body
    assert reader.get_marked().string == source
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize(
    ("quote", "body", "expected"),
    [
        (
            "'",
            r"""\\|\'|\"|\a|\b|\f|\n|\r|\t|\v""",
            "\\|'|" + r'\"|\a|\b|\f|\n|\r|\t|\v',
        ),
        (
            '"',
            r"""\\|\'|\"|\a|\b|\f|\n|\r|\t|\v""",
            "\\|'|\"|\a|\b|\f|\n|\r|\t|\v",
        ),
        ("'", 'a"b', 'a"b'),
        ('"', "a'b", "a'b"),
        ("'", r"\q\#\0\x41\u00e9", r"\q\#\0\x41\u00e9"),
        ('"', r"\q\#\0\x41\u00e9", r"\q\#\0\x41\u00e9"),
        ('"', r"\\n", r"\n"),
    ],
)
def test_quoted_value_decodes_supported_escapes_once(value_reader, quote, body, expected):
    source = quote + body + quote
    reader = value_reader(source + "\r\nNEXT=x")

    assert parse_value(reader) == expected
    assert reader.get_marked().string == source
    assert reader.peek(8) == "\r\nNEXT=x"
    reader.set_mark()
    assert reader.get_marked().line == 2


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("pairs", [1, 2])
def test_even_backslashes_allow_quote_to_close(value_reader, quote, pairs):
    source = quote + "path" + "\\" * (2 * pairs) + quote
    suffix = " # outside " + quote + "\nNEXT=x"
    reader = value_reader(source + suffix)

    assert parse_value(reader) == "path" + "\\" * pairs
    assert reader.get_marked().string == source
    assert reader.peek(len(suffix) + 1) == suffix


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("pairs", [0, 1, 2])
def test_odd_backslashes_escape_quote_inside_value(value_reader, quote, pairs):
    source = quote + "path" + "\\" * (2 * pairs + 1) + quote + "end" + quote
    reader = value_reader(source + "\nNEXT=x")

    assert parse_value(reader) == "path" + "\\" * pairs + quote + "end"
    assert reader.get_marked().string == source
    assert reader.peek(7) == "\nNEXT=x"


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("newline", ["\n", "\r", "\r\n"])
def test_quoted_value_spans_physical_lines(value_reader, quote, newline):
    body = "first" + newline + "  # second\\" + newline + "third"
    source = quote + body + quote
    reader = value_reader(source + newline + "NEXT=x")

    assert parse_value(reader) == body
    assert reader.get_marked().string == source
    assert reader.peek(len(newline) + 6) == newline + "NEXT=x"
    reader.set_mark()
    assert reader.get_marked().line == 4


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("body", ["", "unfinished\r\nstill open", "trailing\\"])
def test_unterminated_quoted_value_raises_without_consuming_input(value_reader, quote, body):
    source = quote + body
    reader = value_reader(source)

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked().string == ""
    assert reader.peek(len(source) + 1) == source


@pytest.mark.parametrize("quote", ["'", '"'])
def test_escaped_quote_at_end_of_input_does_not_close_value(value_reader, quote):
    source = quote + "unfinished\\" + quote
    reader = value_reader(source)

    with pytest.raises(Error):
        parse_value(reader)

    assert reader.get_marked().string == ""
    assert reader.peek(len(source) + 1) == source

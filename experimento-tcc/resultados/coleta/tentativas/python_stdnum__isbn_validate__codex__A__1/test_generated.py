import pytest

from stdnum.exceptions import (
    InvalidChecksum,
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
)
from stdnum.isbn import validate


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        pytest.param('0306406152', '0306406152', id='isbn10'),
        pytest.param('\t 0-306 40615-2 \r\n', '0306406152', id='isbn10-separators'),
        pytest.param('0-8044-2957-x', '080442957X', id='isbn10-lowercase-x'),
        pytest.param('306-40615-2', '0306406152', id='nine-character-numeric'),
        pytest.param('8044 2957 x', '080442957X', id='nine-character-x'),
        pytest.param('1000000060', '1000000060', id='isbn10-zero-check-digit'),
        pytest.param('0000000000', '0000000000', id='isbn10-all-zero'),
        pytest.param(' 978-0-306 40615-7\n', '9780306406157', id='isbn13-978'),
        pytest.param('979-10-90636-07-1', '9791090636071', id='isbn13-979'),
        pytest.param('9780000000040', '9780000000040', id='isbn13-zero-check-digit'),
        pytest.param('9790000000001', '9790000000001', id='isbn13-unchecked-group'),
        pytest.param('９７８\u2011０\u00a0３０６\u201340615-７', '9780306406157', id='unicode-cleaning'),
    ],
)
def test_validate_returns_compact_isbn(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        (' 0-306-40615-2 ', '0306406152'),
        ('8044 2957 x', '080442957X'),
        ('979-10-90636-07-1', '9791090636071'),
    ],
)
def test_validate_with_conversion_disabled(number, expected):
    assert validate(number, convert=False) == expected


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        pytest.param(' 0-306-40615-2 ', '9780306406157', id='isbn10-numeric'),
        pytest.param('0 8044 2957 x', '9780804429573', id='isbn10-x'),
        pytest.param('306-40615-2', '9780306406157', id='nine-character-numeric'),
        pytest.param('8044-2957-x', '9780804429573', id='nine-character-x'),
        pytest.param('1000000060', '9781000000061', id='isbn10-zero-check-digit'),
        pytest.param('978-0-306-40615-7', '9780306406157', id='already-978'),
        pytest.param(' 979 10 90636 07 1 ', '9791090636071', id='already-979'),
    ],
)
def test_validate_with_conversion_enabled(number, expected):
    assert validate(number, convert=True) == expected


@pytest.mark.parametrize('convert', [False, True], ids=['keep', 'convert'])
@pytest.mark.parametrize(
    ('number', 'error'),
    [
        pytest.param('', InvalidFormat, id='empty'),
        pytest.param(' \t- -\n', InvalidFormat, id='separators-only'),
        pytest.param('0', InvalidFormat, id='no-payload'),
        pytest.param(None, InvalidFormat, id='none'),
        pytest.param('03064X6152', InvalidFormat, id='isbn10-x-in-payload'),
        pytest.param('97803064A6157', InvalidFormat, id='isbn13-letter-in-payload'),
        pytest.param('978030640615X', InvalidFormat, id='isbn13-x-as-check-digit'),
        pytest.param('978030640615\u0667', InvalidFormat, id='unmapped-unicode-check-digit'),
        pytest.param('0/306/40615/2', InvalidFormat, id='unsupported-separator'),
        pytest.param('0306\t406152', InvalidFormat, id='internal-tab'),
        pytest.param('123A', InvalidFormat, id='format-before-length'),
        pytest.param('00000000', InvalidLength, id='eight-digit-ean'),
        pytest.param('00000000000', InvalidLength, id='eleven-digits'),
        pytest.param('000000000000', InvalidLength, id='twelve-digit-ean'),
        pytest.param('00000000000000', InvalidLength, id='fourteen-digit-ean'),
        pytest.param('0-306-40615-3', InvalidChecksum, id='isbn10-wrong-check-digit'),
        pytest.param('030640615X', InvalidChecksum, id='isbn10-unexpected-x'),
        pytest.param('030640615A', InvalidChecksum, id='isbn10-letter-as-check-digit'),
        pytest.param('0-8044-2957-0', InvalidChecksum, id='isbn10-missing-x'),
        pytest.param('306406153', InvalidChecksum, id='nine-character-wrong-check-digit'),
        pytest.param('978-0-306-40615-8', InvalidChecksum, id='isbn13-978-wrong-check-digit'),
        pytest.param('9791090636072', InvalidChecksum, id='isbn13-979-wrong-check-digit'),
        pytest.param('9770000000003', InvalidComponent, id='ean-prefix-977'),
        pytest.param('9800000000007', InvalidComponent, id='ean-prefix-980'),
        pytest.param('4006381333931', InvalidComponent, id='valid-non-bookland-ean'),
        pytest.param('9770000000004', InvalidChecksum, id='checksum-before-prefix'),
    ],
)
def test_validate_rejects_invalid_isbn(number, error, convert):
    with pytest.raises(error) as exc_info:
        validate(number, convert=convert)
    assert exc_info.type is error

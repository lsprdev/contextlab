import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '12345678Z',
        '00000001R',
        'K0000000T',
        'L0000001R',
        'M0000022E',
        'X1234567L',
        'Y1234567X',
        'Z1234567R',
        'A58818501',
        'B12345674',
        'P1234567D',
    ],
)
def test_validate_accepts_compact_nifs(number):
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('\t es 12-345 678-z \n', '12345678Z'),
        ('es-m 000 0022-e', 'M0000022E'),
        (' e s - y-123 4567-x ', 'Y1234567X'),
        ('ES-b 123-4567-4', 'B12345674'),
        (' p1234 567-d ', 'P1234567D'),
    ],
)
def test_validate_returns_normalized_nif(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '12345678A',
        'K0000000R',
        'L0000001T',
        'M0000022T',
        'K00000000',
        'X1234567X',
        'Y1234567R',
        'Z1234567L',
        'B12345675',
        'P1234567E',
        ' es-12 345 678-a ',
    ],
)
def test_validate_rejects_wrong_check_digits(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '1234567L',
        '012345678Z',
        'ES-1234567-L',
        'X123456Z',
        'K00000000T',
    ],
)
def test_validate_rejects_wrong_length_with_numeric_interior(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' es - ',
        '1Z',
        '1A345678Z',
        '1234A67L',
        '12.345.678-Z',
        '1234ES5678Z',
        'ESES12345678Z',
        '@12345674',
    ],
)
def test_validate_rejects_malformed_nifs(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert error.type is InvalidFormat

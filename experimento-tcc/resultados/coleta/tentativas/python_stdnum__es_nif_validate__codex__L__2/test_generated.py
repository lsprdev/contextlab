import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '12345678Z',
        '01234567L',
        'X1234567L',
        'Y1234567X',
        'Z1234567R',
        'K1234567L',
        'L0000001R',
        'M1234567L',
        'A12345674',
        'P1234567D',
    ],
)
def test_accepts_valid_nif(number):
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('\t es 12 345-678 z \n', '12345678Z'),
        (' x-123 4567-l ', 'X1234567L'),
        ('E-S l-000 0001-r', 'L0000001R'),
        ('es-p 123-4567 d', 'P1234567D'),
    ],
)
def test_returns_compact_uppercase_nif(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '12345678A',
        '01234567Z',
        'X1234567X',
        'Y1234567R',
        'Z1234567L',
        'K1234567A',
        'L0000001T',
        'M12345674',
        'A12345675',
        'P1234567E',
    ],
)
def test_rejects_incorrect_check_digit(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' es - ',
        '1',
        '1Z',
        'K12A567L',
        '12.45678Z',
        '#12345674',
        'ESES12345678Z',
    ],
)
def test_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        'A1Z',
        '1234567L',
        '012345678Z',
        'es X-123 456-L',
        'K12345678A',
    ],
)
def test_rejects_invalid_length_with_numeric_interior(number):
    with pytest.raises(InvalidLength):
        validate(number)

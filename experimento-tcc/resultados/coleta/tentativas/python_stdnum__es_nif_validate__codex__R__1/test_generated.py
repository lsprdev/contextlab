import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('12345678Z', '12345678Z'),
        ('01234567L', '01234567L'),
        ('\t es 12-345 678-z \n', '12345678Z'),
        ('X1234567L', 'X1234567L'),
        ('Y1234567X', 'Y1234567X'),
        ('Z1234567R', 'Z1234567R'),
        ('e-s y-123 4567-x', 'Y1234567X'),
        ('K1234567L', 'K1234567L'),
        ('L1234567L', 'L1234567L'),
        ('M1234567L', 'M1234567L'),
        ('  es-k 000-0000-t  ', 'K0000000T'),
        ('L0000001R', 'L0000001R'),
        ('M0000022E', 'M0000022E'),
        ('A12345674', 'A12345674'),
        ('B12345674', 'B12345674'),
        ('B1234567D', 'B1234567D'),
        (' es-b 123-4567-d ', 'B1234567D'),
        ('E12345674', 'E12345674'),
    ],
)
def test_validate_returns_compact_nif(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '12345678A',
        '012345670',
        'X1234567T',
        'Y1234567L',
        'Z1234567L',
        'K1234567A',
        'L1234567A',
        'M1234567A',
        'B12345675',
        'B1234567E',
        'es-b 123-4567-e',
    ],
)
def test_validate_rejects_incorrect_check_digit(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '1234567L',
        '012345678Z',
        'es-123 4567-l',
        'K123456A',
        'K01234567L',
        'X123456A',
        'B123456789',
    ],
)
def test_validate_rejects_incorrect_length(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '12A45678Z',
        '12.45678Z',
        '12\u066345678Z',
        'K123A567L',
        'Y123A567X',
        'B123A5674',
        'I12345674',
        'T12345674',
        '@12345674',
        'DE12345678Z',
        'ESES12345678Z',
        'es-K12A-l',
        'K12345678AL',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat):
        validate(number)

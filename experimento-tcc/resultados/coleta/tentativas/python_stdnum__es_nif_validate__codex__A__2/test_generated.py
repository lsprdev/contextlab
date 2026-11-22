import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('12345678Z', '12345678Z'),
        ('00000000T', '00000000T'),
        ('00000001R', '00000001R'),
        ('99999999R', '99999999R'),
        ('K1234567L', 'K1234567L'),
        ('L1234568C', 'L1234568C'),
        ('M0000001R', 'M0000001R'),
        ('X1234567L', 'X1234567L'),
        ('Y1234567X', 'Y1234567X'),
        ('Z1234567R', 'Z1234567R'),
        ('B12345674', 'B12345674'),
        ('B1234567D', 'B1234567D'),
        ('A00000000', 'A00000000'),
        ('A0000000J', 'A0000000J'),
    ],
)
def test_validate_accepts_each_nif_family(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('\t e-s 12 345-678 z \n', '12345678Z'),
        ('es-k 123-4567-l', 'K1234567L'),
        (' es y-123 4567-x ', 'Y1234567X'),
        ('es b-1234567-d', 'B1234567D'),
        ('es W-1234567-4', 'W12345674'),
        ('\u00a0es\u2013１２３４５６７８\u2013z\u00a0', '12345678Z'),
    ],
)
def test_validate_returns_the_compact_identifier(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '12345678A',
        '123456789',
        'K1234567C',
        'L1234568L',
        'M0000001T',
        'M12345674',
        'X1234567X',
        'Y1234567L',
        'Z1234567X',
        'B12345675',
        'B1234567E',
        'es b-1234567-e',
    ],
)
def test_validate_rejects_wrong_check_digits(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        'K000001R',
        'K00000001R',
        '1234567L',
        'X12345678Z',
        'B1234564',
        'ES-K 000001-R',
        'I1234564',
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
        '12',
        'K12A4567L',
        'K12A456L',
        'K12.4567L',
        'K12\t4567L',
        'K\u0661234567L',
        'K\u00b2234567L',
        'FR12345678Z',
        'ESES12345678Z',
        'I12345674',
        'O12345674',
        'T12345674',
        '!12345674',
    ],
)
def test_validate_reports_invalid_format(number):
    with pytest.raises(InvalidFormat) as exc_info:
        validate(number)
    assert exc_info.type is InvalidFormat

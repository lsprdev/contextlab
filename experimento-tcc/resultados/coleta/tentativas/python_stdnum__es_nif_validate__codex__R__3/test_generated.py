import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '00000000T',
        '01234567L',
        '12345678Z',
        '99999999R',
        'K1234567L',
        'L1234567L',
        'M1234567L',
        'K0000000T',
        'X1234567L',
        'Y1234567X',
        'Z1234567R',
        'A58818501',
        'A1234567D',
        'J0000000J',
    ],
)
def test_validate_returns_canonical_nif(number):
    assert validate(number) == number


@pytest.mark.parametrize('prefix', list('ABCDEFGHJNPQRSUVW'))
def test_validate_accepts_each_cif_prefix(prefix):
    number = prefix + '12345674'
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('  12 345-678 z  ', '12345678Z'),
        ('es 00-000-000 t', '00000000T'),
        ('\t e-s - y 123-4567 x \n', 'Y1234567X'),
        (' Es-l 123 4567-l ', 'L1234567L'),
        ('es s-123 4567-d', 'S1234567D'),
    ],
)
def test_validate_returns_normalized_nif(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '12345678A',
        '123456780',
        'K1234567X',
        'L12345674',
        'M1234567R',
        'X1234567X',
        'Y1234567L',
        'Z1234567X',
        'A12345675',
        'A1234567E',
        ' es-a 123-4567 e ',
    ],
)
def test_validate_rejects_wrong_check_character(number):
    with pytest.raises(InvalidChecksum) as error:
        validate(number)
    assert type(error.value) is InvalidChecksum


@pytest.mark.parametrize(
    'number',
    [
        '1234567L',
        '012345678Z',
        'K123456S',
        'K01234567L',
        'X01234567L',
        'A1234564',
        ' es-A 12345678-4 ',
        'I1234567L0'.replace('L', '0'),
        'K1R',
    ],
)
def test_validate_rejects_wrong_length_with_numeric_interior(number):
    with pytest.raises(InvalidLength) as error:
        validate(number)
    assert type(error.value) is InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '',
        'ES - ',
        '1',
        '1Z',
        'K12A4L',
        '123A5678Z',
        'K123A567L',
        'X123.567L',
        'A123/5674',
        'I12345674',
        'O1234567D',
        'T12345674',
        '?1234567L',
        'FR12345678Z',
        'ESES12345678Z',
        'K12ES567L',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert type(error.value) is InvalidFormat

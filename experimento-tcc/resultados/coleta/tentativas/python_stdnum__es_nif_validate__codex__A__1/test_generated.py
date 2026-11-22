import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '12345678Z',
        '00000000T',
        '00000022E',
        '00000023T',
        'K1234567L',
        'L1234567L',
        'M1234567L',
        'M0000001R',
        'X1234567L',
        'Y1234567X',
        'Z1234567R',
        'X0000000T',
        'Y0000000Z',
        'Z0000000M',
        'B58818501',
        'Q0000000J',
    ],
)
def test_validate_returns_valid_canonical_number(number):
    assert validate(number) == number


@pytest.mark.parametrize('prefix', tuple('ABCDEFGHJNPQRSUVW'))
@pytest.mark.parametrize('check_character', ['4', 'D'])
def test_validate_accepts_numeric_and_alphabetic_cif_checksums(prefix, check_character):
    number = f'{prefix}1234567{check_character}'
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('\t 12 345-678-z \n', '12345678Z'),
        ('  es12345678z  ', '12345678Z'),
        ('\t e-s - k 12-34 567 - l \r\n', 'K1234567L'),
        ('Es-y 1234-567 x', 'Y1234567X'),
        ('es b１２３４５６７—４', 'B12345674'),
        (' Es-q 123-4567 d ', 'Q1234567D'),
    ],
)
def test_validate_returns_compact_uppercase_number(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '12345678A',
        '123456789',
        'K1234567D',
        'L12345674',
        'M1234567X',
        'X1234567X',
        'Y1234567L',
        'Z1234567L',
        'B12345675',
        'Q1234567E',
        'es-y 1234-567 l',
    ],
)
def test_validate_rejects_incorrect_checksum(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '123',
        '1234567L',
        '012345678Z',
        'K123456S',
        'es-K01234567L',
        'es x123456-l',
        'B123456744',
    ],
)
def test_validate_rejects_wrong_length_with_numeric_interior(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' \t- es -\n',
        '1',
        '12',
        '1A345678Z',
        'K123456AL',
        'K12A456L',
        'K1\u066234567L',
        '1234.5678Z',
        '1234\t5678Z',
        'X123/567L',
        'I12345674',
        'O1234567D',
        'T12345674',
        '@12345674',
        'PT12345678Z',
        'ESES12345678Z',
        '12345678ZES',
        None,
        123456789,
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert error.type is InvalidFormat

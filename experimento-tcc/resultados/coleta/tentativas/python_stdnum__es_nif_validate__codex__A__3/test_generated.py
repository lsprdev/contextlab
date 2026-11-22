import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '12345678Z',
        '01234567L',
        '00000022E',
        '00000023T',
        'X1234567L',
        'Y1234567X',
        'Z1234567R',
        'K1234567L',
        'L1234567L',
        'M1234567L',
        'M0000000T',
        'A10000040',
        'A1000004J',
    ],
)
def test_validate_returns_valid_compact_number(number):
    assert validate(number) == number


@pytest.mark.parametrize('prefix', list('ABCDEFGHJNPQRSUVW'))
@pytest.mark.parametrize('check_digit', ['4', 'D'])
def test_validate_accepts_both_cif_check_digit_forms(prefix, check_digit):
    number = f'{prefix}1234567{check_digit}'
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('ES12345678Z', '12345678Z'),
        ('12345678z', '12345678Z'),
        ('0123 4567L', '01234567L'),
        ('12345678-Z', '12345678Z'),
        ('\t12345678Z\n', '12345678Z'),
        ('\t e-s y-123 4567-x \n', 'Y1234567X'),
        ('es-k 1234567-l', 'K1234567L'),
        ('  es-b 1234567-d  ', 'B1234567D'),
        ('es–１２３４５６７８\u00a0z', '12345678Z'),
    ],
)
def test_validate_normalizes_input(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' ES - ',
        'K1',
        'K12A4567L',
        'ES-X123A567L',
        '1234.678Z',
        '1234/678Z',
        '1234\t678Z',
        '1234١678Z',
        '1234²678Z',
        'PT12345678Z',
        'ESES12345678Z',
        'I12345674',
        'O1234567D',
        'T12345674',
        '?12345674',
        '١23456784',
        'K12A456L',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as caught:
        validate(number)
    assert type(caught.value) is InvalidFormat


@pytest.mark.parametrize(
    'number',
    [
        '123',
        '1234567L',
        '012345678Z',
        'es-1234567-l',
        'es-012345678-z',
        'X123456L',
        'K12345678Z',
        'A1234564',
        'T12345674D',
    ],
)
def test_validate_rejects_invalid_length(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '12345678L',
        '123456780',
        'X1234567X',
        'Y1234567L',
        'Z1234567X',
        'Z12345670',
        'K1234567X',
        'L1234567R',
        'M12345674',
        'M0000000J',
        'A12345675',
        'A1234567E',
        'A1000004A',
        'es-b 1234567-z',
    ],
)
def test_validate_rejects_invalid_checksum(number):
    with pytest.raises(InvalidChecksum):
        validate(number)

import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('52998224725', '52998224725'),
        ('529.982.247-25', '52998224725'),
        ('\t\n 529 . 982 . 247 - 25 \r\n', '52998224725'),
        ('5-2.9 9822472.5', '52998224725'),
        ('５２９．９８２．２４７−２５', '52998224725'),
        ('529\u00a0982\u2009247 25', '52998224725'),
        ('000.000.001-91', '00000000191'),
        ('12345678909', '12345678909'),
        ('00000000604', '00000000604'),
        ('00000001406', '00000001406'),
        ('00000001830', '00000001830'),
        ('00000001910', '00000001910'),
        ('00000043400', '00000043400'),
    ],
)
def test_validate_returns_compact_cpf(number, expected):
    result = validate(number)
    assert isinstance(result, str)
    assert result == expected


@pytest.mark.parametrize('digit', '123456789')
def test_validate_accepts_nonzero_repeated_digits_with_matching_checksum(digit):
    number = digit * 11
    assert validate(number) == number


@pytest.mark.parametrize('position', range(9))
def test_validate_accounts_for_each_base_digit(position):
    base = '0' * position + '1' + '0' * (8 - position)
    # Increasing weights represent the negatives of the CPF weights modulo 11.
    first = (position + 1) % 10
    second = (position + 9 * first) % 11 % 10
    number = f'{base}{first}{second}'
    assert validate(number) == number


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' .-\t\n ',
        '00000000000',
        '000.000.000-00',
        '0',
        '000000000000',
        '529.982.24A-25',
        '529A',
        '529/982/247-25',
        '+52998224725',
        '529\t98224725',
        '529\n98224725',
        '٥2998224725',
        '⁵2998224725',
        None,
        52998224725,
        b'52998224725',
    ],
)
def test_validate_rejects_invalid_format_before_checking_length(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert type(error.value) is InvalidFormat


@pytest.mark.parametrize(
    'number',
    ['1', '529.982.247', '5299822472', '529982247025', '0529.982.247-25'],
)
def test_validate_rejects_wrong_length_before_checking_checksum(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '52998224735',
        '52998224724',
        '52998224733',
        '529.982.247-52',
        '52998224625',
        '00000000614',
        '00000001831',
        '00000000001',
        '11111111112',
    ],
)
def test_validate_rejects_incorrect_check_digits(number):
    with pytest.raises(InvalidChecksum):
        validate(number)

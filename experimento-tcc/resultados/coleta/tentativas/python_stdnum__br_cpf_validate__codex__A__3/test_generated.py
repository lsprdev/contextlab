import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('52998224725', '52998224725'),
        ('529.982.247-25', '52998224725'),
        ('\t\n529.982.247-25\r\n', '52998224725'),
        ('529 982 247 25', '52998224725'),
        ('.-52 99..82-247 2-5-.', '52998224725'),
        ('５２９．９８２．２４７−２５', '52998224725'),
        ('529\u00a0982\u2009247\u300025', '52998224725'),
        ('012.345.678-90', '01234567890'),
        ('12345678909', '12345678909'),
        ('00000000191', '00000000191'),
        ('00000000604', '00000000604'),
        ('00000009300', '00000009300'),
        ('00000003700', '00000003700'),
    ],
)
def test_validate_returns_compact_cpf(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize('digit', '123456789')
def test_validate_accepts_nonzero_repeated_digits_with_matching_checksum(digit):
    number = digit * 11
    assert validate(number) == number


@pytest.mark.parametrize(
    'number',
    [
        '',
        '\t .- \n',
        '00000000000',
        '000.000.000-00',
        '0',
        '000000000000',
        '529A8224725',
        '529.982.247/25',
        '529,982,247-25',
        '+52998224725',
        '529\t98224725',
        '529\n98224725',
        '٥2998224725',
        '²2998224725',
        '123X',
        None,
        52998224725,
        b'52998224725',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert type(error.value) is InvalidFormat


@pytest.mark.parametrize(
    'number',
    [
        '1',
        '529982247',
        '529.982.247-2',
        '529.982.247-250',
        '052998224725',
        '5299822472500',
    ],
)
def test_validate_rejects_wrong_compact_length(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '529.982.247-35',
        '529.982.247-26',
        '52998224752',
        '12345678919',
        '01234567891',
        '00000000001',
        '00000009310',
        '00000009301',
    ],
)
def test_validate_rejects_incorrect_check_digits(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize('position', range(9))
@pytest.mark.parametrize('digit', '123456789')
def test_validate_checksum_uses_each_payload_position(position, digit):
    base = '0' * position + digit + '0' * (8 - position)
    # With one nonzero payload digit, the ascending weights give the residues directly.
    value = int(digit)
    first = ((position + 1) * value % 11) % 10
    second = ((position * value + 9 * first) % 11) % 10
    number = f'{base}{first}{second}'
    assert validate(number) == number


@pytest.mark.parametrize('suffix', [f'{value:02d}' for value in range(100) if value != 25])
def test_validate_accepts_only_the_matching_checksum_for_a_fixed_base(suffix):
    with pytest.raises(InvalidChecksum):
        validate('529982247' + suffix)

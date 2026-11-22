import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('52998224725', '52998224725'),
        ('529.982.247-25', '52998224725'),
        ('\t 529 . 982 - 247 . 2 5 \n', '52998224725'),
        ('012.345.678-90', '01234567890'),
        ('16899535009', '16899535009'),
        ('00000000191', '00000000191'),
        ('00000000604', '00000000604'),
        ('00000001910', '00000001910'),
        ('111.111.111-11', '11111111111'),
    ],
)
def test_validate_returns_compact_cpf(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' \t.- \n',
        '0',
        '000000000000',
        '000.000.000-00',
        '5299822472X',
        '529.982.247-2X',
        'CPF 529.982.247-25',
        '+52998224725',
        '529/982/247-25',
        '529,982,247-25',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert error.type is InvalidFormat


@pytest.mark.parametrize(
    'number',
    [
        '1',
        '529982247',
        '529.982.247-2',
        '529.982.247-250',
        '00052998224725',
    ],
)
def test_validate_rejects_invalid_compact_length(number):
    with pytest.raises(InvalidLength) as error:
        validate(number)
    assert error.type is InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '529.982.247-35',
        '529.982.247-26',
        '529.982.247-52',
        '529.982.247-33',
        '012.345.678-91',
    ],
)
def test_validate_rejects_incorrect_check_digits(number):
    with pytest.raises(InvalidChecksum) as error:
        validate(number)
    assert error.type is InvalidChecksum


@pytest.mark.parametrize('position', range(9))
def test_validate_rejects_each_single_digit_change_in_the_base(position):
    valid_number = '52998224725'
    for digit in '0123456789':
        if digit == valid_number[position]:
            continue
        changed_number = valid_number[:position] + digit + valid_number[position + 1:]
        with pytest.raises(InvalidChecksum) as error:
            validate(changed_number)
        assert error.type is InvalidChecksum

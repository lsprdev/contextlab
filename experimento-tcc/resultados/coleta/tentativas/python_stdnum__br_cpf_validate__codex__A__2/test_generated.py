import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('52998224725', '52998224725'),
        ('529.982.247-25', '52998224725'),
        ('\t\n  529.982.247-25 \r\n', '52998224725'),
        ('5 29 982 247 25', '52998224725'),
        ('-52--998-224-725-', '52998224725'),
        ('.52..998.224.725.', '52998224725'),
        ('５２９．９８２\u00a0２４７−２５', '52998224725'),
        ('000.000.001-91', '00000000191'),
        ('00000001406', '00000001406'),
        ('12345678909', '12345678909'),
        ('00000001910', '00000001910'),
        ('00000001830', '00000001830'),
        ('00000019100', '00000019100'),
        ('11111111111', '11111111111'),
        ('99999999999', '99999999999'),
    ],
)
def test_validate_returns_compact_cpf(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' .-\t\n',
        '0',
        '00000000000',
        '000.000.000-00',
        '000000000000',
        '12A',
        '529.982.24A-25',
        '+52998224725',
        '529/982.247-25',
        '529\t98224725',
        '529\n98224725',
        '5299822472٥',
        '5299822472⁵',
        None,
        52998224725,
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert type(error.value) is InvalidFormat


@pytest.mark.parametrize(
    'number',
    ['1', '5299822472', '529.982.247-2', '529982247025', '5299822470025'],
)
def test_validate_rejects_wrong_compact_length(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        pytest.param('52998224735', id='first-check-digit'),
        pytest.param('52998224726', id='second-check-digit'),
        pytest.param('529.982.247-52', id='swapped-check-digits'),
        pytest.param('529.982.248-25', id='changed-base-digit'),
        pytest.param('000.000.191-01', id='zero-check-digits'),
        pytest.param('00000000001', id='zero-base-with-nonzero-check-digit'),
    ],
)
def test_validate_rejects_invalid_checksum(number):
    with pytest.raises(InvalidChecksum):
        validate(number)

import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('12345678Z', '12345678Z'),
        ('00000001R', '00000001R'),
        ('91234567F', '91234567F'),
        ('K1234567L', 'K1234567L'),
        ('L1234567L', 'L1234567L'),
        ('M1234567L', 'M1234567L'),
        ('K0000000T', 'K0000000T'),
        ('X1234567L', 'X1234567L'),
        ('Y1234567X', 'Y1234567X'),
        ('Z1234567R', 'Z1234567R'),
        ('A5881850A', 'A5881850A'),
        ('B99286320', 'B99286320'),
        ('B9928632J', 'B9928632J'),
        ('\t es-12 345 678-z \n', '12345678Z'),
        (' e-s-k 123 4567-l ', 'K1234567L'),
        (' y-123 4567-x ', 'Y1234567X'),
        (' eS-a 588 1850-a ', 'A5881850A'),
    ],
)
def test_validate_returns_compact_nif(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize('prefix', tuple('ABCDEFGHJNPQRSUVW'))
def test_validate_accepts_cif_prefixes(prefix):
    number = f'{prefix}58818501'
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'error'),
    [
        ('12345678A', InvalidChecksum),
        ('123456780', InvalidChecksum),
        ('K1234567X', InvalidChecksum),
        ('L1234567X', InvalidChecksum),
        ('M1234567X', InvalidChecksum),
        ('X1234567X', InvalidChecksum),
        ('Y1234567L', InvalidChecksum),
        ('Z1234567L', InvalidChecksum),
        ('A58818502', InvalidChecksum),
        ('A5881850B', InvalidChecksum),
        ('es-y-123 4567-l', InvalidChecksum),
        ('1234567L', InvalidLength),
        ('012345678Z', InvalidLength),
        ('ES-K123456L', InvalidLength),
        ('X01234567L', InvalidLength),
        ('A5881850', InvalidLength),
        ('1A345678Z', InvalidFormat),
        ('1234567AZ', InvalidFormat),
        ('K123A567L', InvalidFormat),
        ('Y123456-A', InvalidLength),
        ('12345A7Z', InvalidFormat),
        ('1234567A9Z', InvalidFormat),
        ('12.345.678Z', InvalidFormat),
        ('1234\t5678Z', InvalidFormat),
        ('ESES12345678Z', InvalidFormat),
        ('12345678ZES', InvalidFormat),
        ('I58818501', InvalidFormat),
        ('O58818501', InvalidFormat),
        ('T58818501', InvalidFormat),
        ('?58818501', InvalidFormat),
    ],
)
def test_validate_raises_specific_error(number, error):
    with pytest.raises(error) as caught:
        validate(number)
    assert type(caught.value) is error

import pytest

from stdnum.exceptions import (
    InvalidChecksum,
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
)
from stdnum.isbn import validate


@pytest.mark.parametrize(
    ('number', 'normalized', 'converted'),
    [
        ('0306406152', '0306406152', '9780306406157'),
        (' \t--0-306 40615-2--\r\n', '0306406152', '9780306406157'),
        ('306-40615-2', '0306406152', '9780306406157'),
        (' 0-9752298-0-x ', '097522980X', '9780975229804'),
        ('97522980x', '097522980X', '9780975229804'),
        ('0140328726', '0140328726', '9780140328721'),
        ('0000000000', '0000000000', '9780000000002'),
        ('\t978-0 306-40615 7\n', '9780306406157', '9780306406157'),
        (' 979-10-90636-07-1 ', '9791090636071', '9791090636071'),
        ('9789999999991', '9789999999991', '9789999999991'),
        ('9799999999990', '9799999999990', '9799999999990'),
    ],
)
def test_validate_normalizes_and_optionally_converts(number, normalized, converted):
    assert validate(number) == normalized
    assert validate(number, convert=False) == normalized
    assert validate(number, convert=True) == converted


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    ('number', 'expected_error'),
    [
        (' -- ', InvalidFormat),
        ('X306406152', InvalidFormat),
        ('0306.406152', InvalidFormat),
        ('3064A6152', InvalidFormat),
        ('97803064X6157', InvalidFormat),
        ('978030640615x', InvalidFormat),
        ('12A4', InvalidFormat),
        ('1234567X', InvalidLength),
        ('96385074', InvalidLength),
        ('03064061520', InvalidLength),
        ('036000291452', InvalidLength),
        ('10012345000017', InvalidLength),
        ('0306406153', InvalidChecksum),
        ('306406153', InvalidChecksum),
        ('030640615A', InvalidChecksum),
        ('0975229800', InvalidChecksum),
        ('9780306406158', InvalidChecksum),
        ('9791090636072', InvalidChecksum),
        ('4006381333932', InvalidChecksum),
        ('400638133393X', InvalidFormat),
        ('4006381333931', InvalidComponent),
        ('4009780000008', InvalidComponent),
        ('9771234567003', InvalidComponent),
        ('9800000000007', InvalidComponent),
    ],
)
def test_validate_raises_the_expected_error(number, expected_error, convert):
    with pytest.raises(expected_error) as caught:
        validate(number, convert=convert)
    assert type(caught.value) is expected_error

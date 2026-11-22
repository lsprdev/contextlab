import pytest

from stdnum.exceptions import (
    InvalidChecksum,
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
)
from stdnum.isbn import validate


@pytest.mark.parametrize(
    ('number', 'canonical', 'converted'),
    [
        ('0306406152', '0306406152', '9780306406157'),
        ('\t 0-306 40615-2 \n', '0306406152', '9780306406157'),
        ('306-40615-2', '0306406152', '9780306406157'),
        ('0-8044-2957-x', '080442957X', '9780804429573'),
        ('8044 2957 x', '080442957X', '9780804429573'),
        ('123456789X', '123456789X', '9781234567897'),
        ('0000000000', '0000000000', '9780000000002'),
        ('9780306406157', '9780306406157', '9780306406157'),
        ('\n978-0 306-40615 7\t', '9780306406157', '9780306406157'),
        ('979-10-90636-07-1', '9791090636071', '9791090636071'),
        ('979-0-00000000-1', '9790000000001', '9790000000001'),
    ],
)
def test_validate_returns_canonical_isbn(number, canonical, converted):
    assert validate(number) == canonical
    assert validate(number, convert=False) == canonical
    assert validate(number, convert=True) == converted


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    ('number', 'error'),
    [
        ('', InvalidFormat),
        ('0- ', InvalidFormat),
        ('03064X6152', InvalidFormat),
        ('97803064X6157', InvalidFormat),
        ('0/306406152', InvalidFormat),
        ('0٣06406152', InvalidFormat),
        ('123A', InvalidLength),
        ('12A4', InvalidFormat),
        ('12345670', InvalidLength),
        ('03064061520', InvalidLength),
        ('036000291452', InvalidLength),
        ('00000000000000', InvalidLength),
        ('0306406153', InvalidChecksum),
        ('306-40615-3', InvalidChecksum),
        ('0804429570', InvalidChecksum),
        ('030640615x', InvalidChecksum),
        ('030640615Q', InvalidChecksum),
        ('978-0-306-40615-8', InvalidChecksum),
        ('9791090636072', InvalidChecksum),
        ('978030640615x', InvalidFormat),
        ('9770000000003', InvalidComponent),
        ('9800000000007', InvalidComponent),
        ('4006381333931', InvalidComponent),
        ('9770000000004', InvalidChecksum),
        ('977000000000x', InvalidFormat),
    ],
)
def test_validate_rejects_invalid_isbn(number, error, convert):
    with pytest.raises(error) as raised:
        validate(number, convert=convert)
    assert type(raised.value) is error

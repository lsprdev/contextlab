import pytest

from stdnum.exceptions import InvalidChecksum, InvalidComponent, InvalidFormat, InvalidLength
from stdnum.isbn import validate


@pytest.mark.parametrize(
    ('number', 'normalized', 'converted'),
    [
        ('0306406152', '0306406152', '9780306406157'),
        ('\t 0-306 40615-2 \r\n', '0306406152', '9780306406157'),
        ('306-40615-2', '0306406152', '9780306406157'),
        ('0-8044-2957-x', '080442957X', '9780804429573'),
        ('8044 2957 x', '080442957X', '9780804429573'),
        ('1-4028-9462-7', '1402894627', '9781402894626'),
        ('0000000000', '0000000000', '9780000000002'),
        ('\t978 0-306-40615-7\n', '9780306406157', '9780306406157'),
        ('9780000000040', '9780000000040', '9780000000040'),
        ('979-10-90636-07-1', '9791090636071', '9791090636071'),
        ('979-0-00000000-1', '9790000000001', '9790000000001'),
    ],
)
def test_validate_normalizes_and_optionally_converts(number, normalized, converted):
    assert validate(number) == normalized
    assert validate(number, convert=True) == converted


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    ('number', 'error'),
    [
        ('0-306-40615-3', InvalidChecksum),
        ('306406153', InvalidChecksum),
        ('0-8044-2957-0', InvalidChecksum),
        ('030640615A', InvalidChecksum),
        ('030640615X', InvalidChecksum),
        ('978-0-306-40615-8', InvalidChecksum),
        ('9791090636072', InvalidChecksum),
        ('9770000000003', InvalidComponent),
        ('9800000000007', InvalidComponent),
        ('9770000000004', InvalidChecksum),
        ('A306406152', InvalidFormat),
        ('03064061X2', InvalidFormat),
        ('0306/406152', InvalidFormat),
        ('978030640615X', InvalidFormat),
        ('97803064061X7', InvalidFormat),
        ('97A0000000003', InvalidFormat),
        ('12A', InvalidFormat),
        (' - ', InvalidFormat),
        ('96385074', InvalidLength),
        ('00306406152', InvalidLength),
        ('036000291452', InvalidLength),
        ('09780306406157', InvalidLength),
    ],
)
def test_validate_raises_exact_validation_error(number, error, convert):
    with pytest.raises(error) as exc_info:
        validate(number, convert=convert)
    assert exc_info.type is error

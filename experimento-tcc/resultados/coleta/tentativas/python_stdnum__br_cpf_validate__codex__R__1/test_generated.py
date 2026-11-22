import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    "number",
    [
        "52998224725",
        "10000000019",
        "01000000028",
        "00100000037",
        "00010000046",
        "00001000055",
        "00000100064",
        "00000010073",
        "00000001082",
        "00000000191",
        "16899535009",
        "00000000604",
        "60000000060",
        "10000001090",
        "19100000000",
    ],
)
def test_validate_returns_valid_cpf_unchanged(number):
    assert validate(number) == number


@pytest.mark.parametrize("digit", "123456789")
def test_validate_accepts_positive_repeated_digits_with_matching_checksum(digit):
    number = digit * 11
    assert validate(number) == number


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("529.982.247-25", "52998224725"),
        ("\t\n  529.982.247-25  \r\n", "52998224725"),
        (".5-2 9.9-8 2.2-4 7-2.5-", "52998224725"),
        (" 000.000.001-91 ", "00000000191"),
    ],
)
def test_validate_returns_compact_cpf(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    "number",
    [
        "",
        "\t \n",
        " .---. ",
        "0",
        "00000000000",
        "000000000000",
        " 000.000.000-00 ",
        "52998224A25",
        "x",
        "+52998224725",
        "52998_224725",
        "529\t98224725",
        "529\n98224725",
        "\U0001e9552998224725",
    ],
)
def test_validate_rejects_invalid_format_before_length_or_checksum(number):
    with pytest.raises(InvalidFormat):
        validate(number)


@pytest.mark.parametrize(
    "number",
    [
        "1",
        "00000000001"[:-1] + "1",
        "529.982.247",
        "529.982.247-2",
        "529.982.247-025",
        "00.529.982.247-25",
    ],
)
def test_validate_checks_compact_length_before_checksum(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    ("body", "checksum"),
    [("529982247", 25), ("000000006", 4), ("600000000", 60)],
)
def test_validate_rejects_every_other_check_digit_pair(body, checksum):
    for candidate in range(100):
        if candidate == checksum:
            continue
        number = f"{body}{candidate:02d}"
        with pytest.raises(InvalidChecksum):
            validate(number)


def test_validate_checks_checksum_after_removing_separators():
    with pytest.raises(InvalidChecksum):
        validate(" 529.982.247-52 ")

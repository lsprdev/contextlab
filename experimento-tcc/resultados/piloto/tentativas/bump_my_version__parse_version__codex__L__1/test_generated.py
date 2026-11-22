import re

import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.serialization import parse_version


def test_returns_named_captures_as_strings():
    pattern = r"\A(v)(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)-(?P<stage>[A-Za-z]+)\Z"

    assert parse_version("v001.02.0-RC", pattern) == {
        "major": "001",
        "minor": "02",
        "patch": "0",
        "stage": "RC",
    }


@pytest.mark.parametrize(
    ("version_string", "expected"),
    [
        ("3", {"major": "3", "stage": "", "build": ""}),
        ("3+007", {"major": "3", "stage": "", "build": "007"}),
        ("3-rc", {"major": "3", "stage": "rc", "build": ""}),
        ("3-rc+007", {"major": "3", "stage": "rc", "build": "007"}),
    ],
)
def test_includes_all_optional_named_groups(version_string, expected):
    pattern = r"\A(?P<major>\d+)(?:-(?P<stage>[a-z]+))?(?:\+(?P<build>\d+))?\Z"

    assert parse_version(version_string, pattern) == expected


def test_preserves_empty_captures_from_participating_groups():
    assert parse_version("v7-", r"v(?P<major>\d+)-(?P<tag>[a-z]*)") == {
        "major": "7",
        "tag": "",
    }


def test_searches_for_the_first_match_inside_the_input():
    assert parse_version("release v02.4 or v9.8 pending", r"v(?P<major>\d+)\.(?P<minor>\d+)") == {
        "major": "02",
        "minor": "4",
    }


def test_uses_verbose_regex_syntax():
    pattern = r"""
        \A v (?P<major>[0-9]+)  # Numeric component
        [ ] \# (?P<label>[A-Z]+)
        \Z
    """

    assert parse_version("v12 #RC", pattern) == {"major": "12", "label": "RC"}


def test_preserves_whitespace_and_unicode_in_captured_text():
    pattern = r"\A(?P<prefix>\s+)(?P<number>\d+)-(?P<label>\w+)(?P<suffix>\s+)\Z"

    assert parse_version(" \t٢-betaé  ", pattern) == {
        "prefix": " \t",
        "number": "٢",
        "label": "betaé",
        "suffix": "  ",
    }


@pytest.mark.parametrize(
    ("version_string", "pattern"),
    [
        ("unknown", r"(?P<major>\d+)"),
        ("release 2.3", r"\A(?P<major>\d+)\.(?P<minor>\d+)\Z"),
        ("2.3-extra", r"\A(?P<major>\d+)\.(?P<minor>\d+)\Z"),
        ("V2", r"v(?P<major>\d+)"),
        ("release\nv2", r"^v(?P<major>\d+)"),
        ("v\n2", r"v.(?P<major>\d+)"),
    ],
)
def test_returns_empty_dict_when_pattern_does_not_match(version_string, pattern):
    assert parse_version(version_string, pattern) == {}


def test_returns_empty_dict_when_match_has_only_unnamed_groups():
    assert parse_version("3.14", r"\A(\d+)\.(\d+)\Z") == {}


@pytest.mark.parametrize(
    ("version_string", "pattern"),
    [
        ("", r"\A(?P<major>\d*)\Z"),
        ("", "("),
        ("1.2.3", ""),
        ("", ""),
    ],
)
def test_returns_empty_dict_for_empty_inputs(version_string, pattern):
    assert parse_version(version_string, pattern) == {}


@pytest.mark.parametrize("pattern", ["(", r"(?P<part>\d+)(?P<part>[a-z]+)"])
def test_wraps_invalid_regex_in_bump_version_error(pattern):
    with pytest.raises(BumpVersionError) as error:
        parse_version("1.2.3", pattern)

    assert str(error.value) == f"'{pattern}' is not a valid regular expression."
    assert isinstance(error.value.__cause__, re.error)

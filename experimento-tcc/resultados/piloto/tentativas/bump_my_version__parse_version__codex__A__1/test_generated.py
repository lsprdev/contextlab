import re

import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.serialization import parse_version


RELEASE_PATTERN = r"\A(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\Z"
PRERELEASE_PATTERN = r"""
    \A
    (?P<major>\d+) \. (?P<minor>\d+) \. (?P<patch>\d+)
    (?:
        - (?P<label>[a-z]+)   # Optional prerelease suffix
        \. (?P<serial>\d+)
    )?
    \Z
"""


def test_returns_named_components_as_original_text():
    assert parse_version("007.00.09", RELEASE_PATTERN) == {
        "major": "007",
        "minor": "00",
        "patch": "09",
    }


@pytest.mark.parametrize(
    ("version", "label", "serial"),
    [
        pytest.param("2.5.0-rc.03", "rc", "03", id="prerelease"),
        pytest.param("2.5.0", "", "", id="release-without-prerelease"),
    ],
)
def test_verbose_pattern_keeps_optional_component_keys(version, label, serial):
    assert parse_version(version, PRERELEASE_PATTERN) == {
        "major": "2",
        "minor": "5",
        "patch": "0",
        "label": label,
        "serial": serial,
    }


def test_search_returns_only_named_groups_from_the_first_match():
    pattern = r"(v)(?P<major>\d+)\.(?P<minor>\d+)"
    assert parse_version("current v12.04, next v90.7", pattern) == {
        "major": "12",
        "minor": "04",
    }


def test_alternation_keeps_the_named_group_from_the_unmatched_branch():
    pattern = r"\A(?:(?P<release>\d+)|dev-(?P<build>\d+))\Z"
    assert parse_version("dev-003", pattern) == {"release": "", "build": "003"}


def test_zero_width_match_preserves_empty_capture_and_lookahead_capture():
    pattern = r"(?P<empty>)(?=(?P<revision>\d))"
    assert parse_version("r8", pattern) == {"empty": "", "revision": "8"}


@pytest.mark.parametrize(
    ("version", "pattern"),
    [
        pytest.param("1.2", RELEASE_PATTERN, id="missing-component"),
        pytest.param("1x2x3", RELEASE_PATTERN, id="wrong-separators"),
        pytest.param("1.2.3-extra", RELEASE_PATTERN, id="anchored-pattern-rejects-suffix"),
        pytest.param("release\nv1", r"^(?P<major>v\d+)$", id="anchors-without-multiline"),
        pytest.param("V1", r"\A(?P<major>v\d+)\Z", id="case-sensitive-by-default"),
        pytest.param("1\n2", r"\A(?P<part>1.2)\Z", id="dot-excludes-newline"),
        pytest.param("v12.5", r"v(\d+)\.(\d+)", id="only-unnamed-groups"),
        pytest.param("stable", r"stable", id="no-capture-groups"),
    ],
)
def test_returns_empty_dict_without_named_results(version, pattern):
    assert parse_version(version, pattern) == {}


@pytest.mark.parametrize(
    ("version", "pattern", "expected"),
    [
        pytest.param("  ", r"\A(?P<part>[ ]+)\Z", {"part": "  "}, id="whitespace-only-version"),
        pytest.param(" 1", r"\A(?P<part>\d+)\Z", {}, id="leading-space-affects-anchor"),
        pytest.param("1 ", r"(?P<part>\d+)\ ", {"part": "1"}, id="escaped-final-space-in-pattern"),
        pytest.param("1 #02", r"(?P<major>\d+)\ \#(?P<build>\d+)", {"major": "1", "build": "02"}, id="escaped-verbose-characters"),
        pytest.param("v١٢", r"\Av(?P<part>\d+)\Z", {"part": "١٢"}, id="unicode-digits"),
        pytest.param("RC7", r"(?i)\A(?P<label>rc)(?P<serial>\d+)\Z", {"label": "RC", "serial": "7"}, id="inline-case-insensitivity"),
    ],
)
def test_respects_literal_input_and_regex_options(version, pattern, expected):
    assert parse_version(version, pattern) == expected


@pytest.mark.parametrize(
    ("version", "pattern"),
    [
        pytest.param("", r"\A(?P<part>\d*)\Z", id="empty-version-even-if-regex-can-match"),
        pytest.param("", "[", id="empty-version-with-invalid-pattern"),
        pytest.param(None, "[", id="absent-version-with-invalid-pattern"),
        pytest.param("1.2.3", "", id="empty-pattern"),
        pytest.param("1.2.3", None, id="absent-pattern"),
    ],
)
def test_missing_input_returns_empty_dict(version, pattern):
    assert parse_version(version, pattern) == {}


@pytest.mark.parametrize(
    "pattern",
    [
        pytest.param(r"(?P<major>\d+", id="unterminated-group"),
        pytest.param(r"(?P<part>\d+)\.(?P<part>\d+)", id="duplicate-group-name"),
    ],
)
def test_invalid_regex_is_reported_as_bumpversion_error(pattern):
    with pytest.raises(BumpVersionError) as error:
        parse_version("1.2.3", pattern)

    assert str(error.value) == f"'{pattern}' is not a valid regular expression."
    assert isinstance(error.value.__cause__, re.error)

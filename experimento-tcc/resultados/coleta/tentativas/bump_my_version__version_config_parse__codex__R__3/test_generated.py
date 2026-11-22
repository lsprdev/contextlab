import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.models import Version
from bumpversion.versioning.version_config import VersionConfig


VERSION_PATTERN = r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)$"


def make_config(pattern):
    return VersionConfig(
        parse=pattern,
        serialize=("{major}.{minor}.{patch}",),
        search="version = {current_version}",
        replace="version = {new_version}",
    )


@pytest.fixture
def version_config():
    return make_config(VERSION_PATTERN)


@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_builds_a_version_from_named_captures(version_config, raise_error):
    version = version_config.parse("0.12.34", raise_error=raise_error)

    assert isinstance(version, Version)
    assert version.version_spec is version_config.version_spec
    assert version.original == "0.12.34"
    assert {name: str(part.value) for name, part in version.values().items()} == {
        "major": "0",
        "minor": "12",
        "patch": "34",
    }


def test_parse_searches_with_verbose_regex_and_preserves_the_full_input():
    config = make_config(
        r"""
        v (?P<major>[0-9]+)  # major version after the prefix
        \. (?P<minor>[0-9]+)
        \. (?P<patch>[0-9]+)
        """
    )
    first_input = "  release v7.12.3 (stable)  "
    second_input = "next release v8.0.1"

    first = config.parse(first_input)
    second = config.parse(second_input)

    assert first is not second
    assert first.original == first_input
    assert second.original == second_input
    assert [str(first[name].value) for name in ("major", "minor", "patch")] == ["7", "12", "3"]
    assert [str(second[name].value) for name in ("major", "minor", "patch")] == ["8", "0", "1"]


def test_parse_creates_components_for_an_unmatched_optional_group():
    config = make_config(r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)(?:\.(?P<patch>[0-9]+))?$")
    expected = config.version_spec.create_version({"major": "5", "minor": "6", "patch": ""})

    version = config.parse("5.6", raise_error=True)

    assert isinstance(version, Version)
    assert version.original == "5.6"
    assert {name: part.value for name, part in version.values().items()} == {
        name: part.value for name, part in expected.values().items()
    }


@pytest.mark.parametrize("version_string", [None, "", "   ", "1.2", "1.2.3-rc1", "release 1.2.3"])
def test_parse_returns_none_for_invalid_input_by_default(version_config, version_string):
    assert version_config.parse(version_string) is None


def test_parse_defaults_to_no_version_string(version_config):
    assert version_config.parse() is None


@pytest.mark.parametrize("version_string", [None, "", "bad version"])
def test_parse_raises_with_the_original_input_and_pattern(version_config, version_string):
    with pytest.raises(BumpVersionError) as exc_info:
        version_config.parse(version_string, raise_error=True)

    assert exc_info.value.message == f"Unable to parse version {version_string} using {VERSION_PATTERN}"


@pytest.mark.parametrize("pattern", ["", r"^([0-9]+)\.([0-9]+)\.([0-9]+)$"])
def test_parse_treats_a_pattern_without_named_captures_as_a_failure(pattern):
    config = make_config(pattern)

    assert config.parse("1.2.3", raise_error=False) is None
    with pytest.raises(BumpVersionError) as exc_info:
        config.parse("1.2.3", raise_error=True)

    assert exc_info.value.message == f"Unable to parse version 1.2.3 using {pattern}"

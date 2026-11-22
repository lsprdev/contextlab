import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning import version_config
from bumpversion.versioning.models import Version
from bumpversion.versioning.version_config import VersionConfig


FORMAT = "{major}.{minor}.{patch}"
PATTERN = r"""
    \A release-
    (?P<major>[0-9]+) \.  # major separator
    (?P<minor>[0-9]+) -
    (?P<patch>[0-9]+) \Z
"""


@pytest.fixture
def config():
    return VersionConfig(parse=PATTERN, serialize=(FORMAT,), search=FORMAT, replace=FORMAT)


@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_uses_configured_pattern_and_preserves_original(config, raise_error):
    version = config.parse("release-12.3-45", raise_error=raise_error)

    assert isinstance(version, Version)
    assert version.version_spec is config.version_spec
    assert version.original == "release-12.3-45"
    assert set(version) == {"major", "minor", "patch"}
    assert str(version["major"].value) == "12"
    assert str(version["minor"].value) == "3"
    assert str(version["patch"].value) == "45"


def test_parse_returns_a_fresh_version_on_each_call(config):
    first = config.parse("release-1.2-3")
    second = config.parse("release-7.8-9")

    assert isinstance(first, Version)
    assert isinstance(second, Version)
    assert first is not second
    assert (first.original, str(first["patch"].value)) == ("release-1.2-3", "3")
    assert (second.original, str(second["patch"].value)) == ("release-7.8-9", "9")


@pytest.mark.parametrize("invalid", [None, "", "12.3.45", "release-12.x-45", "release-12.3-45-extra"])
def test_parse_invalid_version_returns_none_by_default(config, invalid):
    assert config.parse(invalid) is None


def test_parse_without_arguments_returns_none(config):
    assert config.parse() is None


@pytest.mark.parametrize("invalid", [None, "", "release-12.x-45"])
def test_parse_invalid_version_raises_with_input_and_pattern(config, invalid):
    with pytest.raises(BumpVersionError) as error:
        config.parse(invalid, raise_error=True)

    assert str(error.value) == f"Unable to parse version {invalid} using {PATTERN}"


@pytest.mark.parametrize("parsed", [None, {}])
def test_parse_treats_empty_parser_results_as_failures(config, monkeypatch, parsed):
    def parse_version_stub(version_string, pattern):
        assert version_string == "release-12.3-45"
        assert pattern == PATTERN
        return parsed

    def unexpected_create_version(_):
        pytest.fail("Version construction was called without parsed components")

    monkeypatch.setattr(version_config, "parse_version", parse_version_stub)
    monkeypatch.setattr(config.version_spec, "create_version", unexpected_create_version)

    assert config.parse("release-12.3-45") is None
    with pytest.raises(BumpVersionError):
        config.parse("release-12.3-45", raise_error=True)


def test_parse_returns_the_version_created_by_its_spec(config, monkeypatch):
    version = Version(config.version_spec, {}, original="previous input")
    received = []

    def create_version(parts):
        received.append(parts)
        return version

    monkeypatch.setattr(config.version_spec, "create_version", create_version)

    assert config.parse("release-12.3-45") is version
    assert received == [{"major": "12", "minor": "3", "patch": "45"}]
    assert version.original == "release-12.3-45"

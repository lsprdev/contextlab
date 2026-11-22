from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning import version_config
from bumpversion.versioning.models import Version
from bumpversion.versioning.version_config import VersionConfig


PARSE_PATTERN = r"""
    \A release-              # prefix
    (?P<major>[0-9]+) \.
    (?P<minor>[0-9]+) \.
    (?P<patch>[0-9]+)
    \Z
"""


@pytest.fixture
def config():
    return VersionConfig(
        parse=PARSE_PATTERN,
        serialize=("{major}.{minor}.{patch}",),
        search="{current_version}",
        replace="{new_version}",
    )


@pytest.mark.parametrize(
    ("version_string", "expected"),
    [
        ("release-12.3.47", {"major": "12", "minor": "3", "patch": "47"}),
        ("release-0.21.4", {"major": "0", "minor": "21", "patch": "4"}),
    ],
)
@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_builds_version_from_named_groups(config, version_string, expected, raise_error):
    result = config.parse(version_string, raise_error=raise_error)

    assert isinstance(result, Version)
    assert result.version_spec is config.version_spec
    assert {name: component.value for name, component in result.values().items()} == expected
    assert result.original == version_string


@pytest.mark.parametrize(
    "version_string",
    [None, "", "release-1.2", "release-1.2.3-extra", "1.2.3"],
)
def test_parse_returns_none_for_invalid_input_by_default(config, version_string):
    assert config.parse(version_string) is None


@pytest.mark.parametrize("version_string", [None, "", "release-1.two.3"])
def test_parse_raises_with_input_and_regex_when_requested(config, version_string):
    with pytest.raises(BumpVersionError) as error:
        config.parse(version_string, raise_error=True)

    assert str(error.value) == f"Unable to parse version {version_string} using {PARSE_PATTERN}"


def test_parse_without_a_version_string(config):
    assert config.parse() is None

    with pytest.raises(BumpVersionError) as error:
        config.parse(raise_error=True)

    assert str(error.value) == f"Unable to parse version None using {PARSE_PATTERN}"


def test_parse_passes_captures_to_version_factory_and_sets_original(config, monkeypatch):
    version_string = "release-8.6.13"
    captures = {"major": "8", "minor": "6", "patch": "13"}
    created_version = Version(config.version_spec, {}, original="previous value")
    parse_version = Mock(return_value=captures)
    create_version = Mock(return_value=created_version)
    monkeypatch.setattr(version_config, "parse_version", parse_version)
    monkeypatch.setattr(config, "version_spec", SimpleNamespace(create_version=create_version))

    result = config.parse(version_string)

    parse_version.assert_called_once_with(version_string, PARSE_PATTERN)
    create_version.assert_called_once_with(captures)
    assert result is created_version
    assert result.original == version_string


@pytest.mark.parametrize("captures", [None, {}])
@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_does_not_create_version_without_captures(config, monkeypatch, captures, raise_error):
    version_string = "release-8.6.13"
    parse_version = Mock(return_value=captures)
    create_version = Mock()
    monkeypatch.setattr(version_config, "parse_version", parse_version)
    monkeypatch.setattr(config, "version_spec", SimpleNamespace(create_version=create_version))

    if raise_error:
        with pytest.raises(BumpVersionError) as error:
            config.parse(version_string, raise_error=True)
        assert str(error.value) == f"Unable to parse version {version_string} using {PARSE_PATTERN}"
    else:
        assert config.parse(version_string, raise_error=False) is None

    parse_version.assert_called_once_with(version_string, PARSE_PATTERN)
    create_version.assert_not_called()

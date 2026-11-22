from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning import version_config
from bumpversion.versioning.models import Version
from bumpversion.versioning.version_config import VersionConfig


PARSE_PATTERN = r"^(?:release-)?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"


@pytest.fixture
def config():
    return VersionConfig(
        parse=PARSE_PATTERN,
        serialize=("{major}.{minor}.{patch}",),
        search="{current_version}",
        replace="{new_version}",
    )


@pytest.mark.parametrize(
    ("text", "raise_error", "expected"),
    [
        ("2.7.14", False, {"major": "2", "minor": "7", "patch": "14"}),
        ("release-10.0.3", True, {"major": "10", "minor": "0", "patch": "3"}),
    ],
)
def test_parse_returns_named_components_and_preserves_input(config, text, raise_error, expected):
    version = config.parse(text, raise_error=raise_error)

    assert isinstance(version, Version)
    assert version.version_spec is config.version_spec
    assert version.original == text
    assert {name: str(component.value) for name, component in version.values().items()} == expected


@pytest.mark.parametrize("text", [None, "", "2.7", "2.7.14-extra"])
def test_parse_returns_none_for_invalid_input_by_default(config, text):
    assert config.parse(text) is None


def test_parse_without_a_version_string_returns_none(config):
    assert config.parse() is None


@pytest.mark.parametrize("text", [None, "", "release-2.x.14"])
def test_parse_reports_invalid_input_and_pattern_in_strict_mode(config, text):
    with pytest.raises(BumpVersionError) as caught:
        config.parse(text, raise_error=True)

    assert str(caught.value) == f"Unable to parse version {text} using {PARSE_PATTERN}"


def test_parse_passes_captures_to_the_spec_and_returns_its_version(config, monkeypatch):
    text = "release-2.7.14"
    captures = {"major": "2", "minor": "7", "patch": "14"}
    parse_version = Mock(return_value=captures)
    created_version = Version(config.version_spec, {}, original="previous input")
    create_version = Mock(return_value=created_version)
    monkeypatch.setattr(version_config, "parse_version", parse_version)
    monkeypatch.setattr(config, "version_spec", SimpleNamespace(create_version=create_version))

    result = config.parse(text)

    parse_version.assert_called_once_with(text, PARSE_PATTERN)
    create_version.assert_called_once_with(captures)
    assert result is created_version
    assert result.original == text


@pytest.mark.parametrize("parser_result", [None, {}], ids=["no-match", "no-captures"])
def test_parse_rejects_missing_captures_without_creating_a_version(config, monkeypatch, parser_result):
    text = "2.7.14"
    parse_version = Mock(return_value=parser_result)
    create_version = Mock()
    monkeypatch.setattr(version_config, "parse_version", parse_version)
    monkeypatch.setattr(config, "version_spec", SimpleNamespace(create_version=create_version))

    assert config.parse(text, raise_error=False) is None
    with pytest.raises(BumpVersionError) as caught:
        config.parse(text, raise_error=True)

    assert str(caught.value) == f"Unable to parse version {text} using {PARSE_PATTERN}"
    assert parse_version.call_count == 2
    create_version.assert_not_called()

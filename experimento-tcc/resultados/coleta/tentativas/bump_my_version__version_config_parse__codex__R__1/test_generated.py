from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.models import Version
from bumpversion.versioning.version_config import VersionConfig


VERSION_PATTERN = r'''
    v(?P<major>\d+)  # major version after the prefix
    \.(?P<minor>\d+)
    \.(?P<patch>\d+)
'''


def make_config(pattern=VERSION_PATTERN):
    return VersionConfig(
        parse=pattern,
        serialize=("{major}.{minor}.{patch}",),
        search="{current_version}",
        replace="{new_version}",
    )


@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_extracts_components_and_preserves_the_full_input(raise_error):
    config = make_config()
    source = "  release: v12.34.56 (stable)  "

    version = config.parse(source, raise_error=raise_error)

    assert isinstance(version, Version)
    assert version.version_spec is config.version_spec
    assert version.original == source
    assert {name: str(component.value) for name, component in version.values().items()} == {
        "major": "12",
        "minor": "34",
        "patch": "56",
    }


def test_parse_without_arguments_returns_none():
    assert make_config().parse() is None


@pytest.mark.parametrize(
    ("pattern", "source"),
    [
        pytest.param(VERSION_PATTERN, None, id="none"),
        pytest.param(VERSION_PATTERN, "", id="empty-input"),
        pytest.param(VERSION_PATTERN, "release v12.34", id="no-match"),
        pytest.param(r"^v(\d+)\.(\d+)\.(\d+)$", "v12.34.56", id="only-unnamed-groups"),
        pytest.param("", "v12.34.56", id="empty-pattern"),
    ],
)
@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_handles_inputs_without_named_captures(pattern, source, raise_error):
    config = make_config(pattern)
    factory = Mock()
    config.version_spec = SimpleNamespace(create_version=factory)

    if raise_error:
        with pytest.raises(BumpVersionError) as error:
            config.parse(source, raise_error=True)
        assert error.value.message == f"Unable to parse version {source} using {pattern}"
    else:
        assert config.parse(source) is None

    factory.assert_not_called()


def test_parse_passes_an_unmatched_optional_named_group_to_the_version_spec():
    config = make_config(r"^v(?P<major>\d+)?$")
    built_version = Version(config.version_spec, {}, original="previous input")
    factory = Mock(return_value=built_version)
    config.version_spec = SimpleNamespace(create_version=factory)

    version = config.parse("v", raise_error=True)

    factory.assert_called_once_with({"major": ""})
    assert version is built_version
    assert version.original == "v"

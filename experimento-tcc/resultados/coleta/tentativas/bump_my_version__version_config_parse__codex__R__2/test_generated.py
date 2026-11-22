from unittest.mock import Mock

import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.models import Version
from bumpversion.versioning.version_config import VersionConfig


RELEASE_PATTERN = r"\A(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)\Z"


def make_config(pattern=RELEASE_PATTERN):
    return VersionConfig(
        parse=pattern,
        serialize=("{major}.{minor}.{patch}",),
        search="version={current_version}",
        replace="version={new_version}",
    )


@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_builds_version_from_named_groups(raise_error):
    config = make_config()

    version = config.parse("12.0.37", raise_error=raise_error)

    assert isinstance(version, Version)
    assert version.version_spec is config.version_spec
    assert version.original == "12.0.37"
    assert {name: str(part.value) for name, part in version.values().items()} == {
        "major": "12",
        "minor": "0",
        "patch": "37",
    }


def test_parse_searches_with_verbose_pattern_and_preserves_full_input():
    config = make_config(
        r"""
        v (?P<patch>[0-9]+)  # capture order differs from serialization order
        \. (?P<major>[0-9]+)
        \. (?P<minor>[0-9]+)
        """
    )
    source = "  release=v31.4.20 (stable)  "

    version = config.parse(source)

    assert isinstance(version, Version)
    assert version.original == source
    assert str(version["major"].value) == "4"
    assert str(version["minor"].value) == "20"
    assert str(version["patch"].value) == "31"


@pytest.mark.parametrize(
    ("source", "expected_groups"),
    [
        ("07", {"major": "07", "stage": ""}),
        ("07-rc", {"major": "07", "stage": "rc"}),
        ("", None),
    ],
)
def test_parse_passes_captures_to_version_spec(source, expected_groups):
    config = make_config(r"\A(?P<major>[0-9]+)(?:-(?P<stage>[a-z]+))?\Z")
    built_version = Version(config.version_spec, {}, original="old input")
    spec = Mock(spec_set=["create_version"])
    spec.create_version.return_value = built_version
    config.version_spec = spec

    result = config.parse(source)

    if expected_groups is None:
        assert result is None
        spec.create_version.assert_not_called()
    else:
        spec.create_version.assert_called_once_with(expected_groups)
        assert result is built_version
        assert result.original == source


def test_parse_accepts_named_captures_with_only_empty_values():
    config = make_config(r"\Av(?P<stage>[a-z]+)?\Z")
    built_version = Version(config.version_spec, {})
    spec = Mock(spec_set=["create_version"])
    spec.create_version.return_value = built_version
    config.version_spec = spec

    result = config.parse("v", raise_error=True)

    spec.create_version.assert_called_once_with({"stage": ""})
    assert result is built_version
    assert result.original == "v"


def test_parse_defaults_to_no_version():
    config = make_config()

    assert config.parse() is None
    with pytest.raises(BumpVersionError) as exc_info:
        config.parse(raise_error=True)
    assert exc_info.value.message == f"Unable to parse version None using {RELEASE_PATTERN}"


@pytest.mark.parametrize(
    ("pattern", "source"),
    [
        (RELEASE_PATTERN, None),
        (RELEASE_PATTERN, ""),
        (RELEASE_PATTERN, "1.2"),
        (RELEASE_PATTERN, " 1.2.3 "),
        (r"\A([0-9]+)\.([0-9]+)\Z", "1.2"),
        ("", "1.2.3"),
    ],
    ids=["none", "empty-input", "incomplete", "anchored", "unnamed-groups", "empty-pattern"],
)
def test_parse_rejects_inputs_without_named_captures(pattern, source):
    config = make_config(pattern)
    spec = Mock(spec_set=["create_version"])
    config.version_spec = spec

    assert config.parse(source) is None
    assert config.parse(source, raise_error=False) is None
    with pytest.raises(BumpVersionError) as exc_info:
        config.parse(source, raise_error=True)

    assert exc_info.value.message == f"Unable to parse version {source} using {pattern}"
    spec.create_version.assert_not_called()


@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_propagates_version_construction_errors(raise_error):
    config = make_config()
    error = ValueError("invalid component value")
    spec = Mock(spec_set=["create_version"])
    spec.create_version.side_effect = error
    config.version_spec = spec

    with pytest.raises(ValueError) as exc_info:
        config.parse("1.2.3", raise_error=raise_error)

    assert exc_info.value is error
    spec.create_version.assert_called_once_with({"major": "1", "minor": "2", "patch": "3"})

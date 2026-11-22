import re

import pytest

from bumpversion.scm.models import SCMConfig


SEMVER = r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"


@pytest.fixture
def scm_config():
    return SCMConfig(
        tag=False,
        push_tag=False,
        sign_tags=False,
        tag_name="v{new_version}",
        allow_dirty=False,
        commit=False,
        message="Bump version",
        parse_pattern=SEMVER,
    )


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        pytest.param("v02.003.10", "02.003.10", id="preserves-version-text"),
        pytest.param("v1.2.3-rc.4", "1.2.3", id="stops-at-end-of-version"),
        pytest.param("refs/tags/v2.4.8", "2.4.8", id="searches-after-leading-text"),
        pytest.param("v1.2.3/v9.8.7", "1.2.3", id="returns-first-match"),
        pytest.param("vbroken/v4.5.6", "4.5.6", id="searches-past-invalid-version"),
        pytest.param("1.2.3", None, id="requires-configured-prefix"),
        pytest.param("V1.2.3", None, id="case-sensitive-by-default"),
        pytest.param("v-1.2.3", None, id="version-must-follow-prefix"),
        pytest.param("v1.2", None, id="incomplete-version"),
        pytest.param("v1x2x3", None, id="requires-literal-version-separators"),
        pytest.param("", None, id="empty-tag"),
    ],
)
def test_get_version_from_tag_with_standard_pattern(scm_config, tag, expected):
    assert scm_config.get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag_name", "tag", "expected"),
    [
        pytest.param(
            "release[api].+{new_version}",
            "release[api].+3.2.1",
            "3.2.1",
            id="literal-prefix-with-regex-metacharacters",
        ),
        pytest.param(
            "release[api].+{new_version}",
            "releaseaXX3.2.1",
            None,
            id="prefix-does-not-act-as-regex",
        ),
        pytest.param("{new_version}", "3.2.1", "3.2.1", id="empty-prefix"),
        pytest.param("build-", "build-3.2.1", "3.2.1", id="no-placeholder"),
        pytest.param("build-", "3.2.1", None, id="literal-prefix-without-placeholder"),
        pytest.param(
            "v{new_version}-stable",
            "v3.2.1",
            "3.2.1",
            id="configured-suffix-may-be-absent",
        ),
        pytest.param(
            "v{new_version}-stable",
            "v3.2.1-preview",
            "3.2.1",
            id="configured-suffix-may-differ",
        ),
        pytest.param(
            "v{new_version}-copy-{new_version}",
            "v3.2.1-copy-9.8.7",
            "3.2.1",
            id="prefix-ends-at-first-placeholder",
        ),
    ],
)
def test_get_version_from_tag_respects_tag_name(scm_config, tag_name, tag, expected):
    scm_config.tag_name = tag_name

    assert scm_config.get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("parse_pattern", "tag", "expected"),
    [
        pytest.param(r"\\d+\\.\\d+\\.\\d+", "v3.12.7", "3.12.7", id="doubled-backslashes"),
        pytest.param(r"\d+(?:\.\d+)?-rc\d+", "v3.12-rc4", "3.12-rc4", id="custom-version-format"),
        pytest.param(r"alpha\d+|beta\d+", "vbeta12", "beta12", id="alternative-with-prefix"),
        pytest.param(r"alpha\d+|beta\d+", "beta12", None, id="prefix-required-for-all-alternatives"),
        pytest.param(r"\d+(?=-signed)", "v12-signed", "12", id="lookahead-excluded-from-capture"),
        pytest.param(r"\d+(?=-signed)", "v12-unsigned", None, id="lookahead-required"),
        pytest.param(r"\d+$", "v12-rc", None, id="end-anchor-is-honored"),
        pytest.param(r"\d*", "v", "", id="empty-capture-is-a-match"),
        pytest.param(r"(?i)rc\d+", "VRC7", "RC7", id="ignore-case-applies-to-prefix-and-version"),
        pytest.param(r"(?i:rc)\d+", "vRC7", "RC7", id="scoped-flag-inside-version"),
        pytest.param(r"(?i:rc)\d+", "VRC7", None, id="scoped-flag-excludes-prefix"),
        pytest.param(r"(?a)\d+", "v٣", None, id="ascii-flag-excludes-unicode-digit"),
        pytest.param(r"\d+", "v٣", "٣", id="unicode-digit-without-ascii-flag"),
        pytest.param(r"(?m)\d+$", "v12\nv34\nend", "12", id="multiline-end-anchor"),
    ],
)
def test_get_version_from_tag_respects_parse_pattern(scm_config, parse_pattern, tag, expected):
    scm_config.parse_pattern = parse_pattern

    assert scm_config.get_version_from_tag(tag) == expected


def test_get_version_from_tag_keeps_prefix_literal_in_verbose_mode(scm_config):
    scm_config.tag_name = "Release # {new_version}"
    scm_config.parse_pattern = r"(?ix) rc \d+ \. \d+"

    assert scm_config.get_version_from_tag("RELEASE # Rc7.2") == "Rc7.2"
    assert scm_config.get_version_from_tag("RELEASE#Rc7.2") is None


def test_get_version_from_tag_raises_for_invalid_pattern(scm_config):
    scm_config.parse_pattern = "["

    with pytest.raises(re.error):
        scm_config.get_version_from_tag("v1.2.3")

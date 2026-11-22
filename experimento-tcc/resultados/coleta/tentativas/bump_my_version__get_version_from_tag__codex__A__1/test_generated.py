import re

import pytest

from bumpversion.scm.models import SCMConfig


SEMVER_PATTERN = r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"


def make_config(tag_name, parse_pattern):
    return SCMConfig(
        tag=True,
        push_tag=False,
        sign_tags=False,
        tag_name=tag_name,
        allow_dirty=False,
        commit=False,
        message="Bump version",
        parse_pattern=parse_pattern,
    )


@pytest.mark.parametrize(
    "tag_name, tag, expected",
    [
        pytest.param("v{new_version}", "v01.002.3", "01.002.3", id="preserve-version-text"),
        pytest.param("v{new_version}", "v1.2.3-14-gabcdef", "1.2.3", id="git-describe-tail"),
        pytest.param("v{new_version}", "refs/tags/v1.2.3", "1.2.3", id="search-with-leading-text"),
        pytest.param("v{new_version}", "v1.2.3 v4.5.6", "1.2.3", id="first-match"),
        pytest.param("v{new_version}", "release-9.8.7/v1.2.3", "1.2.3", id="skip-version-without-prefix"),
        pytest.param("v{new_version}", "release-1.2.3", None, id="missing-prefix"),
        pytest.param("v{new_version}", "V1.2.3", None, id="prefix-is-case-sensitive-by-default"),
        pytest.param("v{new_version}", "v1.2", None, id="incomplete-version"),
        pytest.param("v{new_version}", "v1x2x3", None, id="literal-version-separators"),
        pytest.param("v{new_version}", "", None, id="empty-tag"),
        pytest.param("pkg[stable]+.{new_version}", "pkg[stable]+.1.2.3", "1.2.3", id="literal-prefix-metacharacters"),
        pytest.param("rel.{new_version}", "relX1.2.3", None, id="prefix-dot-is-literal"),
        pytest.param("release-{new_version}-stable", "release-1.2.3-stable", "1.2.3", id="exclude-template-suffix"),
        pytest.param("release-{new_version}-stable", "release-1.2.3-other", "1.2.3", id="suffix-is-not-required"),
        pytest.param("{new_version}-stable", "1.2.3", "1.2.3", id="empty-prefix"),
        pytest.param("release-", "release-1.2.3", "1.2.3", id="template-without-placeholder"),
        pytest.param("release-", "1.2.3", None, id="whole-template-is-prefix-without-placeholder"),
    ],
)
def test_get_version_from_tag_matches_template_prefix(tag_name, tag, expected):
    config = make_config(tag_name, SEMVER_PATTERN)

    assert config.get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    "tag_name, parse_pattern, tag, expected",
    [
        pytest.param("v{new_version}", r"\\d+\\.\\d+\\.\\d+", "v12.34.56", "12.34.56", id="doubled-backslashes"),
        pytest.param("v{new_version}", r"\\d+\\.\\d+\\.\\d+", "v12x34x56", None, id="doubled-escaped-dots-stay-literal"),
        pytest.param("build-{new_version}", r"[A-Z]\d+|\d{4}-\d{2}", "build-2026-09", "2026-09", id="alternate-version-format"),
        pytest.param("build-{new_version}", r"[A-Z]\d+|\d{4}-\d{2}", "2026-09", None, id="prefix-applies-to-every-alternative"),
        pytest.param("Release-{new_version}", r"(?i)rc\d+", "release-RC07", "RC07", id="ignore-case-in-prefix-and-version"),
        pytest.param("Release #1 {new_version}", r"(?ix) rc \d+", "release #1 RC07", "RC07", id="verbose-mode-with-literal-prefix"),
        pytest.param("v{new_version}", r"(?i:rc)\d+", "vRC07", "RC07", id="scoped-flag-in-version"),
        pytest.param("v{new_version}", r"(?i:rc)\d+", "VRC07", None, id="scoped-flag-leaves-prefix-case-sensitive"),
        pytest.param("v{new_version}", r"\d+", "v١٢", "١٢", id="unicode-digits"),
        pytest.param("v{new_version}", r"(?a)\d+", "v١٢", None, id="ascii-digits-only"),
        pytest.param("{new_version}", r"^\d+$", "build-123", None, id="parse-pattern-start-anchor"),
        pytest.param("v{new_version}", r"\d+$", "v123-extra", None, id="parse-pattern-end-anchor"),
        pytest.param("v{new_version}", r"\d*", "v", "", id="empty-capture-is-a-match"),
    ],
)
def test_get_version_from_tag_honors_parse_pattern(tag_name, parse_pattern, tag, expected):
    config = make_config(tag_name, parse_pattern)

    assert config.get_version_from_tag(tag) == expected


def test_get_version_from_tag_raises_for_invalid_parse_pattern():
    config = make_config("v{new_version}", "[")

    with pytest.raises(re.error):
        config.get_version_from_tag("v1.2.3")

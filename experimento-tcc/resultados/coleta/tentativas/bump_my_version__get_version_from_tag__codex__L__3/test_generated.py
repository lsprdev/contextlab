import re

import pytest

from bumpversion.scm.models import SCMConfig


@pytest.fixture
def make_config():
    def create(tag_name, parse_pattern):
        return SCMConfig(
            tag=True,
            push_tag=False,
            sign_tags=False,
            tag_name=tag_name,
            allow_dirty=False,
            commit=False,
            message="",
            parse_pattern=parse_pattern,
        )

    return create


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        pytest.param("v01.002.3", "01.002.3", id="preserves-version-text"),
        pytest.param("refs/tags/v1.2.3-extra", "1.2.3", id="searches-within-tag"),
        pytest.param("vbad-v2.3.4-v5.6.7", "2.3.4", id="first-valid-match"),
        pytest.param("1.2.3", None, id="missing-prefix"),
        pytest.param("V1.2.3", None, id="case-sensitive-by-default"),
        pytest.param("v1x2x3", None, id="literal-version-separators"),
        pytest.param("v1.2", None, id="incomplete-version"),
        pytest.param("", None, id="empty-tag"),
    ],
)
def test_extracts_version_from_tag(make_config, tag, expected):
    config = make_config("v{new_version}", r"\d+\.\d+\.\d+")
    assert config.get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("refs/tags/pkg.[a]+(rc)?-7.8", "7.8"),
        ("pkgX.[a]+(rc)?-7.8", None),
        ("pkgXaaa(rc)-7.8", None),
    ],
)
def test_treats_template_prefix_as_literal_text(make_config, tag, expected):
    config = make_config("pkg.[a]+(rc)?-{new_version}", r"\d+\.\d+")
    assert config.get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag_name", "tag", "expected"),
    [
        pytest.param("release-{new_version}-stable", "release-12-stable", "12", id="configured-suffix"),
        pytest.param("release-{new_version}-stable", "release-12", "12", id="absent-suffix"),
        pytest.param("release-{new_version}-stable", "release-12-dev", "12", id="different-suffix"),
        pytest.param("pkg-{new_version}-{new_version}", "pkg-12-34", "12", id="repeated-placeholder"),
        pytest.param("release-", "release-12", "12", id="template-without-placeholder"),
        pytest.param("release-", "other-12", None, id="literal-template-required"),
        pytest.param("{new_version}", "refs/tags/12", "12", id="empty-prefix"),
    ],
)
def test_uses_template_text_before_first_version_placeholder(make_config, tag_name, tag, expected):
    config = make_config(tag_name, r"\d+")
    assert config.get_version_from_tag(tag) == expected


def test_normalizes_doubled_backslashes_in_parse_pattern(make_config):
    config = make_config("v{new_version}", r"\\d+\\.\d+\\.\\d+")
    assert config.get_version_from_tag("v12.34.56") == "12.34.56"
    assert config.get_version_from_tag("v12x34x56") is None


def test_returns_whole_version_with_named_and_positional_subgroups(make_config):
    config = make_config(
        "release/{new_version}",
        r"(?P<major>\d+)\.(\d+)\.(\d+)(?:-rc(\d+))?(?:\+([a-z]+))?",
    )
    assert config.get_version_from_tag("release/10.20.30-rc4+build") == "10.20.30-rc4+build"


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("release-dev", "dev"), ("release-42", "42"), ("other-42", None)],
)
def test_requires_prefix_for_each_parse_pattern_alternative(make_config, tag, expected):
    config = make_config("release-{new_version}", r"dev|\d+")
    assert config.get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag_name", "pattern", "tag", "expected"),
    [
        pytest.param("Release-{new_version}", r"(?i)rc\d+", "refs/tags/rELEASE-Rc7", "Rc7", id="ignore-case-applies-to-prefix-and-version"),
        pytest.param("v{new_version}", r"(?s)\d.\d", "v1\n2", "1\n2", id="dot-matches-newline"),
        pytest.param("{new_version}", r"(?m)^\d+$", "header\n12\nfooter", "12", id="multiline-anchors"),
        pytest.param("pkg # {new_version}", r"(?x)\d+ \. \d+", "pkg # 2.5", "2.5", id="verbose-pattern-with-literal-prefix"),
    ],
)
def test_honors_inline_regex_flags(make_config, tag_name, pattern, tag, expected):
    config = make_config(tag_name, pattern)
    assert config.get_version_from_tag(tag) == expected


def test_honors_end_anchor_in_parse_pattern(make_config):
    config = make_config("v{new_version}", r"\d+\.\d+$")
    assert config.get_version_from_tag("refs/tags/v1.2") == "1.2"
    assert config.get_version_from_tag("refs/tags/v1.2-extra") is None


def test_distinguishes_empty_version_match_from_no_match(make_config):
    config = make_config("release-{new_version}", "")
    assert config.get_version_from_tag("release-") == ""
    assert config.get_version_from_tag("other-") is None


def test_invalid_parse_pattern_raises_regex_error(make_config):
    config = make_config("v{new_version}", "[")
    with pytest.raises(re.error):
        config.get_version_from_tag("v1.2.3")

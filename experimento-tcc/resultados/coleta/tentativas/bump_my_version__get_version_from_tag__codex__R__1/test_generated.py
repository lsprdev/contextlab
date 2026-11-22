import re

import pytest

from bumpversion.scm.models import SCMConfig


VERSION = r"\d+\.\d+\.\d+"


def make_config(tag_name="v{new_version}", parse_pattern=VERSION):
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
    ("tag_name", "tag", "expected"),
    [
        pytest.param("v{new_version}", "v12.34.56", "12.34.56", id="standard-tag"),
        pytest.param("v{new_version}", "refs/tags/v1.2.3-local", "1.2.3", id="search-within-tag"),
        pytest.param("v{new_version}", "vbad/v1.2.3/v4.5.6", "1.2.3", id="first-successful-match"),
        pytest.param("v{new_version}", "release-1.2.3", None, id="missing-prefix"),
        pytest.param("v{new_version}", "v-1.2.3", None, id="prefix-adjacency"),
        pytest.param("v{new_version}", "V1.2.3", None, id="case-sensitive-by-default"),
        pytest.param("v{new_version}", "v1x2x3", None, id="literal-version-separators"),
        pytest.param("v{new_version}", "", None, id="empty-tag"),
        pytest.param("{new_version}", "1.2.3", "1.2.3", id="empty-prefix"),
        pytest.param("{new_version}-stable", "1.2.3", "1.2.3", id="empty-prefix-with-suffix"),
        pytest.param("v{new_version}-stable", "v1.2.3", "1.2.3", id="missing-template-suffix"),
        pytest.param("v{new_version}-stable", "v1.2.3-beta", "1.2.3", id="different-tag-suffix"),
        pytest.param("v{new_version}/v{new_version}", "v1.2.3/v4.5.6", "1.2.3", id="first-placeholder"),
        pytest.param("release-", "release-1.2.3", "1.2.3", id="template-without-placeholder"),
        pytest.param("release-", "1.2.3", None, id="literal-template-required"),
        pytest.param("", "build/1.2.3", "1.2.3", id="empty-template"),
        pytest.param("rel[qa].+{new_version}", "rel[qa].+1.2.3", "1.2.3", id="regex-metacharacters-in-prefix"),
        pytest.param("rel[qa].+{new_version}", "relqXXX1.2.3", None, id="prefix-does-not-act-as-regex"),
    ],
)
def test_get_version_from_tag_template(tag_name, tag, expected):
    config = make_config(tag_name=tag_name)

    assert config.get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("parse_pattern", "tag", "expected"),
    [
        pytest.param(r"\\d+\\.\\d+", "v10.20-beta", "10.20", id="doubled-backslashes"),
        pytest.param(r"\\d+\\.\\d+", "v10x20", None, id="doubled-escaped-dot-stays-literal"),
        pytest.param(r"\d+\.\d+", "v10.20-beta", "10.20", id="single-backslashes"),
        pytest.param(
            r"(?P<major>\d+)\.(?P<minor>\d+)(?:-rc\.\d+)?",
            "v12.4-rc.7+build.3",
            "12.4-rc.7",
            id="whole-match-with-inner-captures",
        ),
        pytest.param(r"\d+|nightly", "vnightly-next", "nightly", id="second-alternative"),
        pytest.param(r"\d+|nightly", "release-nightly", None, id="prefix-required-for-each-alternative"),
        pytest.param(r"\d+(?=-stable)", "v42-stable", "42", id="version-lookahead"),
        pytest.param(r"\d+(?=-stable)", "v42-dev", None, id="failed-version-lookahead"),
        pytest.param(r"(?:\d+)?", "v-unversioned", "", id="successful-empty-capture"),
        pytest.param(r"(?:\d+)?", "unversioned", None, id="no-match-with-empty-capable-pattern"),
        pytest.param("", "v", "", id="empty-pattern"),
    ],
)
def test_get_version_from_tag_parse_pattern(parse_pattern, tag, expected):
    config = make_config(parse_pattern=parse_pattern)

    assert config.get_version_from_tag(tag) == expected


def test_get_version_from_tag_normalizes_backslashes_once():
    config = make_config(parse_pattern="build" + "\\" * 4 + r"\d+")

    assert config.get_version_from_tag(r"vbuild\42") == r"build\42"
    assert config.get_version_from_tag("vbuild42") is None


@pytest.mark.parametrize(
    ("tag_name", "parse_pattern", "tag", "expected"),
    [
        pytest.param("rel-{new_version}", r"(?i)[a-z]+\d+", "REL-RC12", "RC12", id="ignore-case-in-prefix-and-version"),
        pytest.param("rel-{new_version}", r"(?i:[a-z]+)\d+", "rel-RC12", "RC12", id="scoped-ignore-case"),
        pytest.param("rel-{new_version}", r"(?i:[a-z]+)\d+", "REL-RC12", None, id="scoped-flag-excludes-prefix"),
        pytest.param("v{new_version}", r"(?is)rc.\d+", "VRC\n42", "RC\n42", id="combined-global-flags"),
        pytest.param("{new_version}", r"(?m)^\d+\.\d+$", "header\n12.34\nfooter", "12.34", id="multiline-anchors"),
        pytest.param("rel # {new_version}", r"(?x)\d+ \. \d+", "rel # 12.34", "12.34", id="verbose-pattern-with-literal-prefix"),
        pytest.param("rel # {new_version}", r"(?x)\d+ \. \d+", "rel12.34", None, id="verbose-prefix-still-required"),
        pytest.param("v{new_version}", r"(?a)\w+", "vé", None, id="ascii-word-class"),
        pytest.param("v{new_version}", r"\w+", "vé", "é", id="unicode-word-class-by-default"),
    ],
)
def test_get_version_from_tag_regex_flags(tag_name, parse_pattern, tag, expected):
    config = make_config(tag_name=tag_name, parse_pattern=parse_pattern)

    assert config.get_version_from_tag(tag) == expected


def test_get_version_from_tag_raises_for_malformed_parse_pattern():
    config = make_config(parse_pattern="[")

    with pytest.raises(re.error):
        config.get_version_from_tag("v1.2.3")

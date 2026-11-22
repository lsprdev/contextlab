import re

import pytest

from bumpversion.scm.models import SCMConfig


@pytest.fixture
def make_config():
    def create(tag_name="v{new_version}", parse_pattern=r"\d+\.\d+\.\d+"):
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

    return create


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        pytest.param("v12.03.456", "12.03.456", id="preserves-version-text"),
        pytest.param("archive/v1.2.3-notes", "1.2.3", id="searches-within-tag"),
        pytest.param("vbroken/v2.3.4-v5.6.7", "2.3.4", id="first-valid-match"),
        pytest.param("release-1.2.3", None, id="missing-prefix"),
        pytest.param("V1.2.3", None, id="case-sensitive-by-default"),
        pytest.param("v1x2x3", None, id="invalid-separators"),
        pytest.param("v1.2", None, id="missing-component"),
        pytest.param("", None, id="empty-tag"),
    ],
)
def test_extracts_version_from_tag(make_config, tag, expected):
    assert make_config().get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag_name", "tag", "expected"),
    [
        pytest.param("pkg.[x]+/{new_version}", "pkg.[x]+/1.2.3", "1.2.3", id="literal-metacharacters"),
        pytest.param("pkg.[x]+/{new_version}", "pkgZxx/1.2.3", None, id="rejects-regex-prefix-lookalike"),
        pytest.param("v{new_version}-stable", "v1.2.3-preview", "1.2.3", id="suffix-may-differ"),
        pytest.param("v{new_version}-{new_version}", "v1.2.3", "1.2.3", id="first-placeholder-ends-prefix"),
        pytest.param("{new_version}-stable", "build/1.2.3", "1.2.3", id="empty-prefix"),
        pytest.param("release-", "release-1.2.3", "1.2.3", id="whole-template-is-prefix-without-placeholder"),
        pytest.param("release-", "other-1.2.3", None, id="requires-prefix-without-placeholder"),
    ],
)
def test_uses_literal_template_prefix(make_config, tag_name, tag, expected):
    assert make_config(tag_name=tag_name).get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("pattern", "tag", "expected"),
    [
        pytest.param(r"(?P<major>\d+)\.(\d+)(?:-rc\d+)?", "v02.7-rc3+meta", "02.7-rc3", id="whole-version-with-inner-groups"),
        pytest.param(r"\d+\.\d+|next", "vnext", "next", id="prefixed-alternative"),
        pytest.param(r"\d+\.\d+|next", "release-next", None, id="prefix-required-for-every-alternative"),
        pytest.param(r"\d+\.\d+$", "v1.2-extra", None, id="respects-pattern-end-anchor"),
        pytest.param(r"\d*", "v", "", id="empty-match-is-a-version-string"),
        pytest.param(r"\\d+\\.\\d+", "v12.34", "12.34", id="normalizes-doubled-escapes"),
        pytest.param(r"[0-9]+\\\\[0-9]+", r"v12\34", r"12\34", id="literal-backslash-after-normalization"),
        pytest.param(r"(?i)rc\d+", "VRC03", "RC03", id="ignore-case-applies-to-prefix-and-version"),
        pytest.param(r"(?im)rc\d+$", "VRC03\nnotes", "RC03", id="combined-global-flags"),
    ],
)
def test_applies_configured_version_pattern(make_config, pattern, tag, expected):
    assert make_config(parse_pattern=pattern).get_version_from_tag(tag) == expected


def test_verbose_pattern_preserves_spaces_and_hash_in_prefix(make_config):
    config = make_config(
        tag_name="release # {new_version}",
        parse_pattern="(?x)\\d+  # major\n \\. \\d+",
    )

    assert config.get_version_from_tag("release # 12.34") == "12.34"
    assert config.get_version_from_tag("release12.34") is None


def test_invalid_version_pattern_raises_regex_error(make_config):
    config = make_config(parse_pattern="[")

    with pytest.raises(re.error):
        config.get_version_from_tag("v1.2.3")

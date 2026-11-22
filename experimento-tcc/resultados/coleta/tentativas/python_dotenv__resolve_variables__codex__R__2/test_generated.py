import os

import pytest

from dotenv.main import resolve_variables


@pytest.fixture(params=[True, False], ids=["dotenv-first", "environment-first"])
def override(request):
    return request.param


def test_empty_iterable_returns_no_bindings(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_ENV_ONLY", "process")

    assert resolve_variables(iter(()), override=override) == {}


def test_preserves_literal_empty_and_valueless_bindings(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_BARE", "process")
    monkeypatch.setenv("RESOLVE_TEST_EMPTY", "process")
    monkeypatch.setenv("RESOLVE_TEST_NONE", "process")
    values = [
        ("RESOLVE_TEST_BARE", "  café $RESOLVE_TEST_BARE\nnext line  "),
        ("RESOLVE_TEST_EMPTY", ""),
        ("RESOLVE_TEST_NONE", None),
    ]

    assert resolve_variables(values, override=override) == dict(values)


@pytest.mark.parametrize(
    ("override", "expected"),
    [(True, "dotenv"), (False, "process")],
    ids=["dotenv-first", "environment-first"],
)
def test_override_only_changes_precedence_when_both_sources_define_a_name(
    monkeypatch, override, expected
):
    monkeypatch.setenv("RESOLVE_TEST_SHARED", "process")
    monkeypatch.setenv("RESOLVE_TEST_ENV_ONLY", "outside")
    monkeypatch.delenv("RESOLVE_TEST_LOCAL_ONLY", raising=False)
    monkeypatch.delenv("RESOLVE_TEST_RESULT", raising=False)
    values = [
        ("RESOLVE_TEST_SHARED", "dotenv"),
        ("RESOLVE_TEST_LOCAL_ONLY", "inside"),
        (
            "RESOLVE_TEST_RESULT",
            "<${RESOLVE_TEST_SHARED:-fallback}:"
            "${RESOLVE_TEST_LOCAL_ONLY}${RESOLVE_TEST_ENV_ONLY}:"
            "${RESOLVE_TEST_SHARED}>",
        ),
    ]

    assert resolve_variables(iter(values), override=override) == {
        "RESOLVE_TEST_SHARED": "dotenv",
        "RESOLVE_TEST_LOCAL_ONLY": "inside",
        "RESOLVE_TEST_RESULT": f"<{expected}:insideoutside:{expected}>",
    }
    assert os.environ["RESOLVE_TEST_SHARED"] == "process"
    assert os.environ["RESOLVE_TEST_ENV_ONLY"] == "outside"
    assert "RESOLVE_TEST_LOCAL_ONLY" not in os.environ
    assert "RESOLVE_TEST_RESULT" not in os.environ


def test_defaults_distinguish_missing_from_empty_and_valueless(monkeypatch, override):
    for name in ("RESOLVE_TEST_MISSING", "RESOLVE_TEST_EMPTY", "RESOLVE_TEST_NONE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RESOLVE_TEST_ENV_EMPTY", "")
    values = [
        ("RESOLVE_TEST_EMPTY", ""),
        ("RESOLVE_TEST_NONE", None),
        (
            "RESULT",
            "[${RESOLVE_TEST_MISSING}][${RESOLVE_TEST_MISSING:-two words}]"
            "[${RESOLVE_TEST_MISSING:-}][${RESOLVE_TEST_EMPTY:-fallback}]"
            "[${RESOLVE_TEST_NONE:-fallback}][${RESOLVE_TEST_ENV_EMPTY:-fallback}]",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_EMPTY": "",
        "RESOLVE_TEST_NONE": None,
        "RESULT": "[][two words][][][][]",
    }


@pytest.mark.parametrize(
    ("override", "expected"),
    [(True, "||"), (False, "process|process|")],
    ids=["dotenv-first", "environment-first"],
)
def test_override_applies_to_empty_and_valueless_dotenv_bindings(
    monkeypatch, override, expected
):
    monkeypatch.setenv("RESOLVE_TEST_EMPTY", "process")
    monkeypatch.setenv("RESOLVE_TEST_NONE", "process")
    monkeypatch.setenv("RESOLVE_TEST_ENV_EMPTY", "")
    values = [
        ("RESOLVE_TEST_EMPTY", ""),
        ("RESOLVE_TEST_NONE", None),
        ("RESOLVE_TEST_ENV_EMPTY", "local"),
        (
            "RESULT",
            "${RESOLVE_TEST_EMPTY:-fallback}|${RESOLVE_TEST_NONE:-fallback}|"
            "${RESOLVE_TEST_ENV_EMPTY:-fallback}",
        ),
    ]

    result = resolve_variables(values, override=override)

    assert result == {
        "RESOLVE_TEST_EMPTY": "",
        "RESOLVE_TEST_NONE": None,
        "RESOLVE_TEST_ENV_EMPTY": "local",
        "RESULT": expected + ("local" if override else ""),
    }


def test_resolves_in_input_order_and_uses_latest_duplicate(monkeypatch, override):
    monkeypatch.delenv("RESOLVE_TEST_ITEM", raising=False)
    monkeypatch.delenv("RESOLVE_TEST_BEFORE", raising=False)
    values = (
        pair
        for pair in [
            ("RESOLVE_TEST_BEFORE", "${RESOLVE_TEST_ITEM:-pending}"),
            ("RESOLVE_TEST_ITEM", "first"),
            ("RESOLVE_TEST_SNAPSHOT", "${RESOLVE_TEST_ITEM}"),
            ("RESOLVE_TEST_ITEM", "${RESOLVE_TEST_ITEM}/second"),
            ("RESOLVE_TEST_AFTER", "${RESOLVE_TEST_BEFORE}:${RESOLVE_TEST_ITEM}"),
        ]
    )

    result = resolve_variables(values, override=override)

    assert list(result.items()) == [
        ("RESOLVE_TEST_BEFORE", "pending"),
        ("RESOLVE_TEST_ITEM", "first/second"),
        ("RESOLVE_TEST_SNAPSHOT", "first"),
        ("RESOLVE_TEST_AFTER", "pending:first/second"),
    ]


def test_environment_reference_before_local_definition(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_LATER", "from environment")
    values = [
        ("BEFORE", "${RESOLVE_TEST_LATER:-fallback}"),
        ("RESOLVE_TEST_LATER", "from input"),
    ]

    assert resolve_variables(values, override=override) == {
        "BEFORE": "from environment",
        "RESOLVE_TEST_LATER": "from input",
    }


def test_does_not_recursively_expand_substituted_text(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_INDIRECT", "${RESOLVE_TEST_INNER}")
    monkeypatch.setenv("RESOLVE_TEST_INNER", "expanded")
    monkeypatch.delenv("RESOLVE_TEST_COPY", raising=False)
    values = [
        ("RESOLVE_TEST_COPY", "${RESOLVE_TEST_INDIRECT}"),
        ("RESULT", "${RESOLVE_TEST_COPY}/${RESOLVE_TEST_INNER}"),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_COPY": "${RESOLVE_TEST_INNER}",
        "RESULT": "${RESOLVE_TEST_INNER}/expanded",
    }


def test_reads_environment_as_input_is_consumed(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_DYNAMIC", "first")

    def values():
        yield "BEFORE", "${RESOLVE_TEST_DYNAMIC}"
        monkeypatch.setenv("RESOLVE_TEST_DYNAMIC", "second")
        yield "AFTER", "${RESOLVE_TEST_DYNAMIC}"

    assert resolve_variables(values(), override=override) == {
        "BEFORE": "first",
        "AFTER": "second",
    }

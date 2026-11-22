import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize("override", [False, True])
def test_empty_iterable_returns_empty_mapping(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_ENV_ONLY", "ambient")

    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize("override", [False, True])
def test_literals_empty_strings_and_none_are_preserved(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_NONE", "ambient")
    monkeypatch.setenv("RESOLVE_TEST_EMPTY", "ambient")
    monkeypatch.setenv("RESOLVE_TEST_BARE", "ambient")
    values = [
        ("RESOLVE_TEST_NONE", None),
        ("RESOLVE_TEST_EMPTY", ""),
        ("RESOLVE_TEST_LITERAL", "  café\n$RESOLVE_TEST_BARE ${unclosed  "),
    ]

    assert resolve_variables(values, override=override) == dict(values)


@pytest.mark.parametrize("override, preferred", [(False, "ambient"), (True, "local")])
def test_precedence_combines_environment_and_resolved_values(monkeypatch, override, preferred):
    monkeypatch.setenv("RESOLVE_TEST_SHARED", "ambient")
    monkeypatch.setenv("RESOLVE_TEST_ENV_ONLY", "external")
    monkeypatch.delenv("RESOLVE_TEST_LOCAL_ONLY", raising=False)
    monkeypatch.delenv("RESOLVE_TEST_CHAIN", raising=False)
    values = [
        ("RESOLVE_TEST_SHARED", "local"),
        ("RESOLVE_TEST_LOCAL_ONLY", "inside"),
        (
            "RESOLVE_TEST_CHAIN",
            "pre[${RESOLVE_TEST_SHARED}${RESOLVE_TEST_ENV_ONLY}]"
            "-${RESOLVE_TEST_LOCAL_ONLY}-${RESOLVE_TEST_SHARED}!",
        ),
        ("RESOLVE_TEST_FINAL", "<${RESOLVE_TEST_CHAIN}>"),
    ]
    combined = f"pre[{preferred}external]-inside-{preferred}!"

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_SHARED": "local",
        "RESOLVE_TEST_LOCAL_ONLY": "inside",
        "RESOLVE_TEST_CHAIN": combined,
        "RESOLVE_TEST_FINAL": f"<{combined}>",
    }
    assert os.environ["RESOLVE_TEST_SHARED"] == "ambient"
    assert os.environ["RESOLVE_TEST_ENV_ONLY"] == "external"
    assert "RESOLVE_TEST_LOCAL_ONLY" not in os.environ


@pytest.mark.parametrize("override", [False, True])
def test_defaults_distinguish_absent_empty_none_and_nonempty_values(monkeypatch, override):
    for name in ("MISSING", "LOCAL_EMPTY", "LOCAL_NONE", "LOCAL_VALUE"):
        monkeypatch.delenv(f"RESOLVE_TEST_{name}", raising=False)
    monkeypatch.setenv("RESOLVE_TEST_ENV_EMPTY", "")
    monkeypatch.setenv("RESOLVE_TEST_ENV_VALUE", "ambient")
    values = [
        ("RESOLVE_TEST_LOCAL_EMPTY", ""),
        ("RESOLVE_TEST_LOCAL_NONE", None),
        ("RESOLVE_TEST_LOCAL_VALUE", "local"),
        (
            "RESULT",
            "[${RESOLVE_TEST_MISSING}][${RESOLVE_TEST_MISSING:-fallback}]"
            "[${RESOLVE_TEST_MISSING:-}][${RESOLVE_TEST_LOCAL_EMPTY:-fallback}]"
            "[${RESOLVE_TEST_LOCAL_NONE:-fallback}][${RESOLVE_TEST_ENV_EMPTY:-fallback}]"
            "[${RESOLVE_TEST_LOCAL_VALUE:-fallback}][${RESOLVE_TEST_ENV_VALUE:-fallback}]",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_LOCAL_EMPTY": "",
        "RESOLVE_TEST_LOCAL_NONE": None,
        "RESOLVE_TEST_LOCAL_VALUE": "local",
        "RESULT": "[][fallback][][][][][local][ambient]",
    }


@pytest.mark.parametrize(
    "override, none_reference, empty_reference",
    [(False, "ambient-none", "ambient-empty"), (True, "", "")],
)
def test_precedence_applies_to_none_and_empty_bindings(
    monkeypatch, override, none_reference, empty_reference
):
    monkeypatch.setenv("RESOLVE_TEST_NONE", "ambient-none")
    monkeypatch.setenv("RESOLVE_TEST_EMPTY", "ambient-empty")
    values = [
        ("RESOLVE_TEST_NONE", None),
        ("RESOLVE_TEST_EMPTY", ""),
        ("RESULT", "${RESOLVE_TEST_NONE:-fallback}|${RESOLVE_TEST_EMPTY:-fallback}"),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_NONE": None,
        "RESOLVE_TEST_EMPTY": "",
        "RESULT": f"{none_reference}|{empty_reference}",
    }


@pytest.mark.parametrize("override", [False, True])
def test_forward_and_self_references_use_only_available_values(monkeypatch, override):
    monkeypatch.delenv("RESOLVE_TEST_LATER", raising=False)
    monkeypatch.delenv("RESOLVE_TEST_SELF", raising=False)
    monkeypatch.setenv("RESOLVE_TEST_LATER_WITH_ENV", "ambient")
    values = [
        ("BEFORE", "${RESOLVE_TEST_LATER:-early}|${RESOLVE_TEST_LATER_WITH_ENV}"),
        ("RESOLVE_TEST_SELF", "${RESOLVE_TEST_SELF:-seed}/self"),
        ("RESOLVE_TEST_LATER", "ready"),
        ("RESOLVE_TEST_LATER_WITH_ENV", "local"),
        ("AFTER", "${RESOLVE_TEST_LATER}|${RESOLVE_TEST_SELF}"),
    ]

    assert resolve_variables(values, override=override) == {
        "BEFORE": "early|ambient",
        "RESOLVE_TEST_SELF": "seed/self",
        "RESOLVE_TEST_LATER": "ready",
        "RESOLVE_TEST_LATER_WITH_ENV": "local",
        "AFTER": "ready|seed/self",
    }


@pytest.mark.parametrize("override", [False, True])
def test_duplicate_bindings_replace_prior_values_in_iteration_order(monkeypatch, override):
    monkeypatch.delenv("RESOLVE_TEST_DUPLICATE", raising=False)
    values = iter([
        ("RESOLVE_TEST_DUPLICATE", "first"),
        ("BEFORE", "${RESOLVE_TEST_DUPLICATE}"),
        ("RESOLVE_TEST_DUPLICATE", "${RESOLVE_TEST_DUPLICATE}/second"),
        ("AFTER", "${RESOLVE_TEST_DUPLICATE}"),
        ("RESOLVE_TEST_DUPLICATE", None),
        ("LAST", "[${RESOLVE_TEST_DUPLICATE:-fallback}]"),
    ])

    assert list(resolve_variables(values, override=override).items()) == [
        ("RESOLVE_TEST_DUPLICATE", None),
        ("BEFORE", "first"),
        ("AFTER", "first/second"),
        ("LAST", "[]"),
    ]


@pytest.mark.parametrize("override", [False, True])
def test_expansion_does_not_reparse_substituted_text(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_TEMPLATE", "${RESOLVE_TEST_TARGET}")
    monkeypatch.setenv("RESOLVE_TEST_TARGET", "expanded")
    monkeypatch.delenv("RESOLVE_TEST_COPY", raising=False)
    values = [
        ("RESOLVE_TEST_COPY", "${RESOLVE_TEST_TEMPLATE}"),
        ("RESULT", "${RESOLVE_TEST_COPY}/${RESOLVE_TEST_TARGET}"),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_COPY": "${RESOLVE_TEST_TARGET}",
        "RESULT": "${RESOLVE_TEST_TARGET}/expanded",
    }


@pytest.mark.parametrize("override", [False, True])
def test_environment_is_read_as_bindings_are_consumed(monkeypatch, override):
    name = "RESOLVE_TEST_CHANGING"
    monkeypatch.setenv(name, "before iteration")

    def bindings():
        monkeypatch.setenv(name, "first")
        yield "FIRST", "${RESOLVE_TEST_CHANGING}"
        monkeypatch.setenv(name, "second")
        yield "SECOND", "${RESOLVE_TEST_CHANGING}"
        monkeypatch.delenv(name)
        yield "THIRD", "${RESOLVE_TEST_CHANGING:-gone}"

    assert resolve_variables(bindings(), override=override) == {
        "FIRST": "first",
        "SECOND": "second",
        "THIRD": "gone",
    }


@pytest.mark.parametrize("override", [False, True])
def test_prior_results_do_not_supply_bindings_to_later_calls(monkeypatch, override):
    monkeypatch.delenv("RESOLVE_TEST_PRIVATE", raising=False)
    first = resolve_variables([("RESOLVE_TEST_PRIVATE", "first call")], override=override)
    second = resolve_variables(
        [("RESULT", "${RESOLVE_TEST_PRIVATE:-missing}")], override=override
    )

    assert first == {"RESOLVE_TEST_PRIVATE": "first call"}
    assert second == {"RESULT": "missing"}

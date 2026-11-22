import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize("override", [False, True])
def test_empty_iterable_returns_empty_mapping(override):
    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize(
    ("override", "expected"),
    [(False, "process"), (True, "dotenv")],
)
def test_precedence_when_both_sources_define_a_variable(monkeypatch, override, expected):
    monkeypatch.setenv("RV_SHARED", "process")
    monkeypatch.setenv("RV_ENV_ONLY", "external")
    monkeypatch.delenv("RV_LOCAL_ONLY", raising=False)
    values = [
        ("RV_SHARED", "dotenv"),
        ("RV_LOCAL_ONLY", "internal"),
        ("RESULT", "${RV_SHARED:-default}/${RV_ENV_ONLY}/${RV_LOCAL_ONLY}"),
    ]

    assert resolve_variables(values, override=override) == {
        "RV_SHARED": "dotenv",
        "RV_LOCAL_ONLY": "internal",
        "RESULT": f"{expected}/external/internal",
    }


@pytest.mark.parametrize(
    ("override", "expected"),
    [(False, "process|process|"), (True, "||dotenv")],
)
def test_empty_and_valueless_bindings_participate_in_precedence(
    monkeypatch, override, expected
):
    monkeypatch.setenv("RV_VALUELESS", "process")
    monkeypatch.setenv("RV_EMPTY_LOCAL", "process")
    monkeypatch.setenv("RV_EMPTY_ENV", "")
    values = [
        ("RV_VALUELESS", None),
        ("RV_EMPTY_LOCAL", ""),
        ("RV_EMPTY_ENV", "dotenv"),
        (
            "RESULT",
            "${RV_VALUELESS:-fallback}|${RV_EMPTY_LOCAL:-fallback}|${RV_EMPTY_ENV:-fallback}",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "RV_VALUELESS": None,
        "RV_EMPTY_LOCAL": "",
        "RV_EMPTY_ENV": "dotenv",
        "RESULT": expected,
    }


@pytest.mark.parametrize("override", [False, True])
def test_defaults_apply_only_to_absent_names(monkeypatch, override):
    for name in ("RV_MISSING", "RV_EMPTY", "RV_VALUELESS"):
        monkeypatch.delenv(name, raising=False)
    values = [
        ("RV_EMPTY", ""),
        ("RV_VALUELESS", None),
        (
            "RESULT",
            "[${RV_MISSING}][${RV_MISSING:-fallback}][${RV_MISSING:-}]"
            "[${RV_EMPTY:-fallback}][${RV_VALUELESS:-fallback}]",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "RV_EMPTY": "",
        "RV_VALUELESS": None,
        "RESULT": "[][fallback][][][]",
    }


@pytest.mark.parametrize("override", [False, True])
def test_resolves_in_input_order_and_uses_latest_binding(monkeypatch, override):
    for name in ("RV_NAME", "RV_LATER", "RV_ALIAS"):
        monkeypatch.delenv(name, raising=False)
    values = iter([
        ("BEFORE", "${RV_NAME:-missing}/${RV_LATER:-later}"),
        ("RV_NAME", "${RV_NAME:-initial}"),
        ("RV_ALIAS", "prefix-${RV_NAME}"),
        ("RV_NAME", "${RV_NAME}-updated"),
        ("RV_LATER", "${RV_ALIAS}/${RV_NAME}"),
        ("AFTER", "${RV_LATER}"),
        ("RV_NAME", None),
        ("AFTER_CLEAR", "[${RV_NAME:-fallback}]"),
    ])

    assert resolve_variables(values, override=override) == {
        "BEFORE": "missing/later",
        "RV_NAME": None,
        "RV_ALIAS": "prefix-initial",
        "RV_LATER": "prefix-initial/initial-updated",
        "AFTER": "prefix-initial/initial-updated",
        "AFTER_CLEAR": "[]",
    }


@pytest.mark.parametrize("override", [False, True])
def test_expands_braced_references_and_preserves_other_text(monkeypatch, override):
    monkeypatch.setenv("RV_TOKEN", "azul")
    monkeypatch.setenv("RV_RAW", "${RV_TOKEN}")
    values = [
        ("LITERAL", "  café\n$RV_TOKEN ${RV_TOKEN-unclosed"),
        ("MIXED", " início\n${RV_TOKEN}${RV_TOKEN}/$RV_TOKEN/${RV_RAW}\nfim "),
    ]

    assert resolve_variables(values, override=override) == {
        "LITERAL": "  café\n$RV_TOKEN ${RV_TOKEN-unclosed",
        "MIXED": " início\nazulazul/$RV_TOKEN/${RV_TOKEN}\nfim ",
    }


@pytest.mark.parametrize("override", [False, True])
def test_reads_current_environment_as_the_iterable_is_consumed(monkeypatch, override):
    monkeypatch.setenv("RV_STREAM", "first")

    def values():
        yield "FIRST", "${RV_STREAM}"
        monkeypatch.setenv("RV_STREAM", "second")
        yield "SECOND", "${RV_STREAM}"
        monkeypatch.delenv("RV_STREAM")
        yield "THIRD", "${RV_STREAM:-removed}"

    assert resolve_variables(values(), override=override) == {
        "FIRST": "first",
        "SECOND": "second",
        "THIRD": "removed",
    }


@pytest.mark.parametrize("override", [False, True])
def test_resolution_leaves_environment_and_subsequent_calls_independent(monkeypatch, override):
    monkeypatch.setenv("RV_EXISTING", "original")
    monkeypatch.delenv("RV_NEW", raising=False)

    assert resolve_variables(
        [("RV_EXISTING", "replacement"), ("RV_NEW", "local")], override=override
    ) == {"RV_EXISTING": "replacement", "RV_NEW": "local"}
    assert os.environ["RV_EXISTING"] == "original"
    assert "RV_NEW" not in os.environ
    assert resolve_variables(
        [("RESULT", "${RV_EXISTING}/${RV_NEW:-missing}")], override=override
    ) == {"RESULT": "original/missing"}

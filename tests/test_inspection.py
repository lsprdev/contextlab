import io
import json

import pytest
from rich.console import Console

from contextlab.inspection import case_results
from contextlab.project_cli import show_attempt


def phases(name, outcome="passed", *, expected=False, failure_phase="call"):
    return [{"nodeid": "::" + name, "when": when,
             "outcome": outcome if when == failure_phase else "passed",
             "expected_failure": expected,
             "assertion_failure": when == "call" and outcome == "failed",
             "message": "assert Decimal('1.00') == Decimal('2.00') [literal]" if outcome == "failed" else None}
            for when in ("setup", "call", "teardown")]


def render(tmp_path, evaluation, *, record_extra=None, **options):
    record = {"evaluation": evaluation, **(record_extra or {})}
    (tmp_path / "record.json").write_text(json.dumps(record))
    output = io.StringIO()
    show_attempt(tmp_path, Console(file=output, width=140, color_system=None), **options)
    return output.getvalue()


def test_show_lists_parameterized_cases_once_then_failure_without_executing_submission(tmp_path):
    rows = phases("test_conversion[0]") + phases("test_conversion[1]") + phases("test_precision", "failed")
    evaluation = {"status": "completed", "approval": "rejected",
                  "original": {"raw": {"collected": 3, "reports": rows}}}
    submission = tmp_path / "test_generated.py"
    submission.write_text("raise RuntimeError('This code must never execute during show')\n")
    before = submission.read_bytes()
    output = render(tmp_path, evaluation)
    assert output.startswith("2 passaram · 1 falhou\n")
    assert "Reprovada" in output
    assert output.count("test_conversion[0]") == 1
    assert output.count("test_conversion[1]") == 1
    assert output.index("test_conversion[0]") < output.index("Detalhes das falhas")
    assert "assert Decimal('1.00') == Decimal('2.00') [literal]" in output
    assert "RuntimeError" not in output
    assert submission.read_bytes() == before
    assert "RuntimeError" in render(tmp_path, evaluation, code=True)


@pytest.mark.parametrize("failure_phase", ["setup", "teardown"])
def test_failed_setup_or_teardown_is_one_error_even_with_passing_call(failure_phase):
    cases = case_results({"reports": phases("test_example", "failed", failure_phase=failure_phase)})
    assert len(cases) == 1
    assert cases[0]["status"] == "error"


def test_skip_xfail_xpass_and_incomplete_are_not_active_passes(tmp_path):
    rows = (phases("test_skip", "skipped") + phases("test_xfail", "skipped", expected=True)
            + phases("test_xpass", expected=True) + phases("test_partial")[:2])
    assert [c["status"] for c in case_results({"reports": rows})] == ["skipped", "xfail", "xfail", "incomplete"]
    output = render(tmp_path, {"status": "timeout", "approval": "not_applicable",
                               "original": {"raw": {"reports": rows, "collected": 5}}})
    assert "1 ignorado · 2 marcados xfail · 1 incompleto" in output
    assert "1 caso(s) sem registro de execução; resultado desconhecido" in output
    assert "timeout" in output
    assert "passaram" not in output


@pytest.mark.parametrize("evaluation", [None, {"status": "infrastructure_error", "approval": "not_applicable",
                                              "error": "Docker unavailable"}])
def test_missing_evaluation_results_are_not_zero_failures(tmp_path, evaluation):
    output = render(tmp_path, evaluation)
    assert "Resultados por caso indisponíveis" in output
    assert "0 falharam" not in output
    assert "Reprovada" not in output
    if evaluation:
        assert "Docker unavailable" in output


def test_collection_error_is_explained_without_inventing_a_test_case(tmp_path):
    output = render(tmp_path, {"status": "completed", "approval": "rejected", "original": {
        "raw": {"collected": 0, "reports": [], "collection_errors": [
            {"nodeid": "test_generated.py", "message": "ImportError: missing_module"}]}}})
    assert "Com registro de execução: 0" in output
    assert "Erro ao coletar testes: test_generated.py" in output
    assert "ImportError: missing_module" in output
    assert "1 falhou" not in output


def test_show_uses_latest_review_and_json_is_machine_readable(tmp_path):
    first = {"status": "completed", "approval": "pending_review"}
    latest = {"status": "completed", "approval": "rejected", "review": {"behavioral_assertions": False},
              "original": {"raw": {"collected": 1, "reports": phases("test_recent")}}}
    extra = {"reviewed_evaluation": latest}
    output = render(tmp_path, first, record_extra=extra)
    assert "1 passou" in output
    assert "Reprovada" in output
    assert "A revisão reprovou as verificações de comportamento" in output
    assert "revisão mais recente" in output
    assert json.loads(render(tmp_path, first, record_extra=extra, raw_json=True)) == latest

import csv
import json
from pathlib import Path

from contextlab.reporting import report_run


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _approved(line=0.5, branch=None, defects=()):
    return {"status": "completed", "received": True, "syntax_ok": True,
            "active_started": True, "reference_passed": True,
            "approval": "approved", "approved": True,
            "coverage_main": {"line_rate": line, "branch_rate": branch},
            "defects": list(defects)}


def _record(evaluation=None, status="finished", gen_status="completed"):
    return {"status": status, "generation": {"status": gen_status, "seconds": 1.2,
                                             "input_tokens": None, "output_tokens": None},
            "evaluation": evaluation}


def _run(tmp_path, records, *, phase="demo", defects=False):
    plan = []
    targets = []
    for i, (target, condition, record) in enumerate(records, 1):
        if target not in [entry["id"] for entry in targets]:
            targets.append({"id": target, "defects": [{"id": "boundary"}] if defects else []})
        row = {"id": f"row-{i}", "order": i, "project": "project", "target": target,
               "agent": "agent", "condition": condition, "repetition": i}
        plan.append(row)
        if record is not None:
            _write(tmp_path / row["id"] / "record.json", record)
    header = {"config": {"phase": phase, "projects": [{"id": "project", "targets": targets}]},
              "plan": plan}
    _write(tmp_path / "run.json", header)
    return report_run(tmp_path)


def test_all_planned_invalid_pending_and_infrastructure_stay_distinct(tmp_path):
    review_pending = _approved(1.0)
    review_pending.update(approval="pending_review", approved=False, coverage_main=None,
                          coverage_raw={"line_rate": 1.0})
    report = _run(tmp_path, [
        ("f", "L", _record(_approved())),
        ("f", "L", _record(status="invalid_submission")),
        ("f", "L", _record(review_pending)),
        ("f", "L", _record({"status": "infrastructure_error", "approval": "not_applicable"})),
        ("f", "L", _record(status="infrastructure_error", gen_status="infrastructure_error")),
        ("f", "L", None),
    ])
    summary = report["summary"]
    assert summary["planned"] == 6
    assert summary["generation_observable"] == 4
    assert summary["pending"] == 1
    assert summary["generation_infrastructure"] == 1
    assert summary["evaluation_infrastructure"] == 1
    assert summary["approval_pending"] == 1
    assert summary["approval_known_n"] == 2
    assert summary["approval_rate_known"] == 0.5
    assert summary["approval_rate"] is None
    assert summary["line_rate_approved"] == 0.5
    assert summary["line_rate_approved_n"] == 1
    assert report["rows"][2]["approved"] is None
    assert report["rows"][2]["line_rate"] is None
    csv_rows = list(csv.DictReader((tmp_path / "results.csv").open()))
    assert len(csv_rows) == 6
    assert csv_rows[0]["input_tokens"] == ""
    assert csv_rows[0]["branch_rate"] == ""
    assert csv_rows[2]["approved"] == ""
    assert report["demonstration"] is True
    assert "DEMONSTRAÇÃO AUTORAL" in (tmp_path / "report.md").read_text()


def test_invalid_suites_are_zero_per_defect_infrastructure_is_excluded(tmp_path):
    detected = {"id": "boundary", "eligible": True, "status": "detected", "detected": True}
    report = _run(tmp_path, [
        ("f", "R", _record(_approved(defects=[detected]))),
        ("f", "R", _record(status="invalid_submission")),
        ("f", "R", _record({"status": "infrastructure_error", "approval": "not_applicable"})),
        ("f", "R", _record(status="infrastructure_error", gen_status="infrastructure_error")),
    ], defects=True)
    defect = report["defects"][0]
    assert defect["generation_observable"] == 3
    assert defect["generation_infrastructure"] == 1
    assert defect["measurement_infrastructure_excluded"] == 1
    assert defect["observable_denominator"] == 2
    assert defect["known_n"] == 2
    assert defect["detected"] == 1
    assert defect["rate_all_observable"] == 0.5
    assert defect["complete"] is True
    assert report["inventory"][0]["validated"] is True


def test_attribution_pending_and_timeout_are_not_zero_known(tmp_path):
    pending = {"id": "boundary", "eligible": True, "status": "pending_attribution", "detected": None}
    timeout = {"id": "boundary", "eligible": True, "status": "timeout", "detected": None}
    report = _run(tmp_path, [
        ("f", "R", _record(_approved(defects=[pending]))),
        ("f", "R", _record(_approved(defects=[timeout]))),
        ("f", "R", _record(status="invalid_submission")),
    ], defects=True)
    defect = report["defects"][0]
    assert defect["observable_denominator"] == 3
    assert defect["known_n"] == 1
    assert defect["unresolved"] == 2
    assert defect["timeouts"] == 1
    assert defect["rate_all_observable"] is None
    assert defect["complete"] is False


def test_configured_defect_is_not_claimed_validated_without_evidence(tmp_path):
    report = _run(tmp_path, [("f", "L", _record(status="invalid_submission"))], defects=True)
    assert report["inventory"][0]["validated"] is None
    assert report["defects"][0]["observable_denominator"] == 1
    assert report["defects"][0]["rate_all_observable"] is None


def test_reviewed_evaluation_overrides_original_pending_review(tmp_path):
    original = _approved()
    original.update(approved=False, approval="pending_review", coverage_main=None)
    record = _record(original)
    record["reviewed_evaluation"] = _approved(0.75)
    report = _run(tmp_path, [("f", "L", record)], phase="pilot")
    assert report["summary"]["approval_rate"] == 1.0
    assert report["summary"]["line_rate_approved"] == 0.75
    assert not report["demonstration"]


def test_contrasts_give_equal_weight_to_functions_not_repetitions(tmp_path):
    rejected = {"status": "completed", "approval": "rejected", "approved": False}
    records = []
    for _ in range(3):
        records.extend([("large", "L", _record(_approved())), ("large", "A", _record(rejected))])
    records.extend([("small", "L", _record(rejected)), ("small", "A", _record(_approved()))])
    report = _run(tmp_path, records)
    contrast = next(item for item in report["contrasts"] if item["project"] is None and
                    item["contrast"] == "L-A" and item["metric"] == "approval_rate")
    assert contrast["functions_comparable"] == 2
    assert contrast["difference_equal_function_weight"] == 0.0
    assert [item["difference"] for item in contrast["function_differences"]] == [1.0, -1.0]


def test_raw_coverage_of_failed_suite_never_becomes_primary(tmp_path):
    rejected = {"status": "completed", "approval": "rejected", "approved": False,
                "coverage_raw": {"line_rate": 1.0, "branch_rate": 1.0}}
    report = _run(tmp_path, [("f", "L", _record(rejected))])
    assert report["summary"]["line_rate_approved"] is None
    assert report["rows"][0]["line_rate"] is None


def test_actual_broker_effort_and_total_evaluation_seconds_are_exported(tmp_path):
    native = _record(_approved())
    native["generation"]["context_stats"] = {"chars_used": 1200, "tool_calls": 4}
    native["evaluation"].update(seconds=0.1, total_seconds=2.5)
    fixture = _record(_approved())
    fixture["generation"]["usage"] = {"chars_used": 600, "tool_calls": 2}
    fixture["evaluation"]["seconds"] = 0.4
    report = _run(tmp_path, [("f", "A", native), ("f", "A", fixture)])
    summary = report["summary"]
    assert summary["context_chars_mean"] == 900
    assert summary["context_chars_n"] == 2
    assert summary["context_chars_complete"] is True
    assert summary["tool_calls_mean"] == 3
    assert summary["evaluation_seconds_mean"] == 1.45
    assert summary["input_tokens_mean"] is None
    assert summary["input_tokens_n"] == 0
    assert summary["input_tokens_complete"] is False
    csv_rows = list(csv.DictReader((tmp_path / "results.csv").open()))
    assert csv_rows[0]["context_chars"] == "1200"
    assert csv_rows[0]["tool_calls"] == "4"
    assert csv_rows[0]["evaluation_seconds"] == "2.5"
    assert csv_rows[1]["input_tokens"] == ""

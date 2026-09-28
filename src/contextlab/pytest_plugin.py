"""Instrumentation loaded only inside the evaluation process (never generation).

Coverage uses public coverage.py APIs. The AST selects only the focal function's
own body; collection/import coverage and nested definitions are excluded.
"""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path

import coverage
import pytest


class Instrumentation:
    def __init__(self):
        self.output = Path(os.environ["CONTEXTLAB_REPORT"])
        self.target = json.loads(os.environ["CONTEXTLAB_TARGET"])
        self.root = Path(os.environ["CONTEXTLAB_PROJECT"])
        self.reports = []
        self.collection_errors = []
        self.collected = 0
        self.cov = coverage.Coverage(branch=True, config_file=False, data_file=None,
                                     source=[str(self.root)])
        self.cov.start()
        self.cov.switch_context("collection")

    def pytest_collection_finish(self, session):
        self.collected = len(session.items)

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_errors.append({"nodeid": report.nodeid,
                                           "message": str(report.longrepr)[-10000:]})

    def pytest_runtest_setup(self, item):
        self.cov.switch_context("test:" + item.nodeid + ":setup")

    def pytest_runtest_call(self, item):
        self.cov.switch_context("test:" + item.nodeid + ":call")

    def pytest_runtest_teardown(self, item):
        self.cov.switch_context("test:" + item.nodeid + ":teardown")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        exception = call.excinfo.type.__name__ if call.excinfo else None
        self.reports.append({
            "nodeid": report.nodeid, "when": report.when, "outcome": report.outcome,
            "exception": exception,
            "assertion_failure": bool(call.excinfo and
                (call.excinfo.errisinstance(AssertionError) or exception == "Failed")),
            "expected_failure": bool(item.get_closest_marker("xfail") is not None or
                                     hasattr(report, "wasxfail")),
            "message": str(report.longrepr)[-10000:] if report.failed else None,
        })
        self.cov.switch_context("between_tests")

    def pytest_sessionfinish(self, session, exitstatus):
        self.cov.stop()
        report = {"exit_code": int(exitstatus), "collected": self.collected,
                  "reports": self.reports, "collection_errors": self.collection_errors}
        try:
            active = {row["nodeid"] for row in self.reports if row["when"] == "call"
                      and row["outcome"] != "skipped" and not row["expected_failure"]}
            contexts = [r"^test:" + re.escape(nodeid) + r":(?:setup|call|teardown)$"
                        for nodeid in active]
            self.cov.get_data().set_query_contexts(contexts or [r"^__no_active_test__$"])
            report["focal"] = focal_coverage(self.cov, self.root / self.target["path"],
                                              self.target["symbol"])
        except Exception as exc:
            report["focal"] = None
            report["coverage_error"] = f"{type(exc).__name__}: {exc}"
        self.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


def focal_body_lines(source: str, symbol: str) -> set[int]:
    """Return physical body lines minus nested functions/classes, headers, docs.

    Symbols may name module functions or Class.method. Nested focal functions
    are deliberately unsupported: their construction requires calling an outer
    function and would change the unit of comparison.
    """
    tree = ast.parse(source)
    current = tree
    for index, part in enumerate(symbol.split(".")):
        found = [node for node in current.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                 and node.name == part]
        if len(found) != 1:
            raise ValueError(f"Focal symbol not uniquely found: {symbol}")
        current = found[0]
        if index < len(symbol.split(".")) - 1 and not isinstance(current, ast.ClassDef):
            raise ValueError("Nested focal functions are not supported")
    if not isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValueError("The focal symbol must be a function or method")
    # A same-line body cannot be separated from its import-time definition
    # by line coverage. Exclude these targets instead of claiming execution.
    if current.body[0].lineno == current.lineno:
        raise ValueError("One-line focal definitions are outside the supported selection criteria")
    allowed = set(range(current.body[0].lineno, current.end_lineno + 1))
    for node in ast.walk(current):
        if node is current:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            allowed.difference_update(range(first, node.end_lineno + 1))
    if isinstance(current.body[0], ast.Expr) and isinstance(current.body[0].value, ast.Constant) and isinstance(current.body[0].value.value, str):
        allowed.difference_update(range(current.body[0].lineno, current.body[0].end_lineno + 1))
    return allowed


def focal_coverage(cov, path: Path, symbol: str) -> dict:
    allowed = focal_body_lines(path.read_text(encoding="utf-8"), symbol)
    _, statements, _, missing, _ = cov.analysis2(str(path))
    executable = set(statements) & allowed
    covered = executable - set(missing)
    stats = {line: exits for line, exits in cov.branch_stats(str(path)).items()
             if line in executable}
    total_exits = sum(total for total, _ in stats.values())
    taken_exits = sum(taken for _, taken in stats.values())
    return {"executed": bool(covered), "line_total": len(executable),
            "line_covered": len(covered),
            "line_rate": len(covered) / len(executable) if executable else None,
            "branch_total": total_exits, "branch_covered": taken_exits,
            "branch_rate": taken_exits / total_exits if total_exits else None,
            "executable_lines": sorted(executable), "covered_lines": sorted(covered),
            "branches": {str(line): {"total": total, "covered": taken}
                         for line, (total, taken) in stats.items()}}


def pytest_configure(config):
    if "CONTEXTLAB_REPORT" in os.environ:
        config.pluginmanager.register(Instrumentation(), "contextlab-instrumentation")

"""Separate, reproducible execution of submitted suites and fixed defects.

Docker is the default. The local backend is intentionally restricted to explicit
trusted demonstrations: it provides no OS security boundary. Reports from code
under evaluation are evidence for researcher review, not adversarial attestation.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

_IGNORE = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
_REVIEW_KEYS = ("behavioral_assertions", "no_target_mock", "no_production_changes")


def _json_write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path outside project: {relative}")
    return path


def _copy_project(project, destination, exclude=()):
    root = Path(project["root"]).resolve()
    patterns = project.get("evaluation_include")
    files = set()
    if patterns:
        for pattern in patterns:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                raise ValueError("evaluation_include must stay inside the project")
            files.update(path for path in root.glob(pattern) if path.is_file())
    else:
        files = {path for path in root.rglob("*") if path.is_file()}
    for path in sorted(files):
        relative = path.relative_to(root)
        if relative.as_posix() in exclude or any(part in _IGNORE for part in relative.parts):
            continue
        # Symlinks may reach data which was not part of the declared project.
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Symlink in evaluation snapshot: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def _reserved_paths(project, target):
    """Reserved tests and their conftests are absent from generated-suite runs."""
    paths = set()
    targets = list(project.get("targets", [])) + [target]
    for unit in targets:
        reserved = list(unit.get("reference_tests", [])) + [d["witness"] for d in unit.get("defects", [])]
        for selection in reserved:
            path = Path(selection.split("::", 1)[0])
            paths.add(path.as_posix())
            for parent in path.parents:
                paths.add((parent / "conftest.py").as_posix())
    return paths


def _digest_tree(root):
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and not any(p in _IGNORE for p in path.relative_to(root).parts):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _syntax(path):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        return None
    except (SyntaxError, UnicodeError) as exc:
        return f"{type(exc).__name__}: {exc}"


def _summarize(report):
    rows = report.get("reports", [])
    calls = [row for row in rows if row["when"] == "call"]
    active = [row for row in calls if row["outcome"] != "skipped" and not row["expected_failure"]]
    failures = []
    if report.get("collection_errors"):
        failures.append("collection_error")
    for row in rows:
        if row["outcome"] == "failed":
            category = ("setup_error" if row["when"] == "setup" else
                        "teardown_error" if row["when"] == "teardown" else
                        "assertion_failure" if row["assertion_failure"] else "execution_error")
            if category not in failures:
                failures.append(category)
    return {"collected": report.get("collected", 0), "active_started": bool(active),
            "active_count": len(active),
            "passed_count": sum(row["outcome"] == "passed" for row in active),
            "skipped_count": sum(row["outcome"] == "skipped" and not row["expected_failure"] for row in rows),
            "xfail_count": len({row["nodeid"] for row in rows if row["expected_failure"]}),
            "failure_categories": failures,
            "reference_passed": bool(active and report.get("exit_code") == 0 and not failures),
            "assertion_failure": any(row["when"] == "call" and row["assertion_failure"] and
                                      row["outcome"] == "failed" and not row["expected_failure"]
                                      for row in rows)}


def _stop_run(process, backend: str, container_name: str) -> list[str]:
    """Bounded cleanup for timeout or operator interruption on POSIX hosts."""
    errors = []
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # The process can exit between wait interruption and cleanup.
    except OSError as exc:
        errors.append(f"kill process group: {exc}")
    try:
        process.wait(timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"wait for child: {exc}")
    if backend == "docker":
        try:
            removed = subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=10)
            if removed.returncode:
                errors.append("docker rm returned non-zero; the --rm container may already have exited")
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"remove evaluator container: {exc}")
    return errors


def _run(snapshot: Path, target: dict, test_paths: list[str], result_dir: Path,
         project: dict, config: dict, submission: Path | None = None) -> dict:
    """Run pytest against a snapshot. No generation caller should import this."""
    result_dir.mkdir(parents=True, exist_ok=True)
    timeout = float(config.get("timeout_seconds", 30))
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    backend = config.get("backend", "docker")
    if backend not in {"docker", "local"}:
        raise ValueError("backend must be docker or local")
    if backend == "local" and config.get("trusted_local") is not True:
        raise ValueError("Local evaluation requires trusted_local=True; use Docker for generated code")
    if backend == "local":
        try:
            dependency_check = subprocess.run(
                [sys.executable, "-I", "-c", "import pytest,coverage; print(pytest.__version__, coverage.__version__)"],
                capture_output=True, text=True, timeout=10, cwd=result_dir)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "infrastructure_error", "error": f"Evaluator dependency preflight failed: {exc}"}
        if dependency_check.returncode or dependency_check.stdout.strip() != "8.4.2 7.10.7":
            return {"status": "infrastructure_error", "error":
                    "Evaluator requires pytest==8.4.2 and coverage==7.10.7 in a virtual environment. "
                    "Packages installed only in the user site are intentionally unavailable to the isolated child."}
    plugin_dir = result_dir / "instrumentation"
    plugin_dir.mkdir(exist_ok=True)
    shutil.copyfile(Path(__file__).with_name("pytest_plugin.py"), plugin_dir / "contextlab_pytest_plugin.py")
    (plugin_dir / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    # Immutable inputs mounted separately from writable reports in Docker.
    roots = project.get("source_roots", ["."])
    for source_root in roots:
        if source_root != ".":
            _inside(snapshot, source_root)
    report_file = result_dir / "pytest_report.json"
    report_file.unlink(missing_ok=True)  # Never reuse evidence from a prior invocation.
    before = _digest_tree(snapshot)
    container_name = "contextlab-eval-" + uuid.uuid4().hex
    if backend == "docker":
        if not shutil.which("docker"):
            return {"status": "infrastructure_error", "error": "Docker executable unavailable"}
        command = ["docker", "run", "--rm", "--name", container_name,
                   "--network=none", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--pids-limit=128",
                   "--memory=" + str(config.get("memory", "1g")), "--cpus=" + str(config.get("cpus", "1")),
                   "--user", f"{os.getuid()}:{os.getgid()}",
                   "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
                   "--mount", f"type=bind,src={snapshot},dst=/project,readonly",
                   "--mount", f"type=bind,src={plugin_dir},dst=/instrumentation,readonly",
                   "--mount", f"type=bind,src={result_dir},dst=/results",
                   "--workdir", "/project"]
        env_values = {"CONTEXTLAB_REPORT": "/results/pytest_report.json",
                      "CONTEXTLAB_PROJECT": "/project", "CONTEXTLAB_TARGET": json.dumps(target),
                      "PYTHONPATH": ":".join(["/instrumentation", "/project"] +
                                             ["/project/" + root for root in roots]),
                      "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
                      "HOME": "/tmp"}
        for key, value in env_values.items():
            command += ["-e", f"{key}={value}"]
        if submission:
            command += ["--mount", f"type=bind,src={submission.parent},dst=/submission,readonly"]
        command += [config.get("image", "contextlab-evaluator:local"), "python", "-m", "pytest",
                    "-p", "contextlab_pytest_plugin", "-p", "no:cacheprovider", "-c", "/instrumentation/pytest.ini",
                    "--rootdir=/project", "--import-mode=importlib", "--tb=short", "-q"]
        command += ["/submission/" + submission.name] if submission else ["/project/" + p for p in test_paths]
        env = None
    else:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(result_dir),
               "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
               "PYTHONPATH": os.pathsep.join([str(plugin_dir), str(snapshot)] +
                                              [str(snapshot / root) for root in roots]),
               "CONTEXTLAB_REPORT": str(report_file), "CONTEXTLAB_PROJECT": str(snapshot),
               "CONTEXTLAB_TARGET": json.dumps(target)}
        command = [sys.executable, "-m", "pytest", "-p", "contextlab_pytest_plugin", "-p", "no:cacheprovider",
                   "-c", str(plugin_dir / "pytest.ini"), "--rootdir=" + str(snapshot),
                   "--import-mode=importlib", "--tb=short", "-q"]
        command += [str(submission)] if submission else [str(snapshot / p) for p in test_paths]
    started = time.monotonic()
    try:
        with (result_dir / "stdout.log").open("wb") as stdout, (result_dir / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(command, cwd=snapshot, env=env, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                cleanup_errors = _stop_run(process, backend, container_name)
                return {"status": "timeout", "seconds": time.monotonic() - started,
                        "cleanup_errors": cleanup_errors,
                        "production_unchanged": before == _digest_tree(snapshot)}
            except KeyboardInterrupt:
                cleanup_errors = _stop_run(process, backend, container_name)
                if cleanup_errors:
                    _json_write(result_dir / "cleanup_errors.json", cleanup_errors)
                raise  # The orchestrator records interruption, never a test failure.
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "infrastructure_error", "error": str(exc), "seconds": time.monotonic() - started}
    if not report_file.exists():
        return {"status": "infrastructure_error", "error": "pytest did not produce its instrumentation report; check stderr.log and evaluator dependencies/image",
                "exit_code": code, "seconds": time.monotonic() - started}
    try:
        raw = json.loads(report_file.read_text())
    except (ValueError, OSError) as exc:
        return {"status": "infrastructure_error", "error": str(exc)}
    unchanged = before == _digest_tree(snapshot)
    if code in (3, 4) or (raw.get("coverage_error") and unchanged):
        return {"status": "infrastructure_error", "error": raw.get("coverage_error", "pytest internal/usage error"),
                "raw": raw, "seconds": time.monotonic() - started, "production_unchanged": unchanged}
    return {"status": "completed", "seconds": time.monotonic() - started, "exit_code": code,
            "production_unchanged": unchanged,
            **_summarize(raw), "focal": raw.get("focal"), "raw": raw}


def _patch(snapshot, defect):
    path = _inside(snapshot, defect["path"])
    source = path.read_text(encoding="utf-8")
    if not defect["old"] or source.count(defect["old"]) != 1:
        raise ValueError(f"Defect {defect['id']} requires exactly one match")
    updated = source.replace(defect["old"], defect["new"], 1)
    ast.parse(updated, filename=str(path))
    path.write_text(updated, encoding="utf-8")


def _validate_one(project, target, defect, out, config):
    with tempfile.TemporaryDirectory(prefix="contextlab-validation-") as tmp:
        original = Path(tmp) / "original"
        _copy_project(project, original)
        project_hash = _digest_tree(original)
        witness = defect["witness"]
        _inside(original, witness.split("::", 1)[0])
        baseline = _run(original, target, [witness], out / "witness_original", project, config)
        mutated = Path(tmp) / "mutated"
        shutil.copytree(original, mutated)
        try:
            _patch(mutated, defect)
        except (ValueError, SyntaxError, OSError) as exc:
            return {"id": defect["id"], "eligible": False, "reason": str(exc), "baseline": baseline}
        change = _run(mutated, target, [witness], out / "witness_mutated", project, config)
        eligible = bool(baseline.get("reference_passed") and baseline.get("production_unchanged") and
                        (baseline.get("focal") or {}).get("executed") and
                        change.get("status") == "completed" and change.get("active_started") and
                        change.get("production_unchanged") and change.get("failure_categories") and
                        set(change["failure_categories"]) <= {"assertion_failure", "execution_error"})
        return {"id": defect["id"], "eligible": eligible, "project_sha256": project_hash,
                "definition_sha256": hashlib.sha256(json.dumps(defect, sort_keys=True).encode()).hexdigest(),
                "reason": None if eligible else "Witness must execute the target, pass original, and fail during the mutant test call",
                "baseline": baseline, "mutated": change}


def validate_defects(project, target, output_dir, config) -> dict:
    """Validate reserved references and each witness; never count them as generated tests."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="contextlab-reference-") as tmp:
        snapshot = Path(tmp) / "project"
        _copy_project(project, snapshot)
        reference_tests = target.get("reference_tests", [])
        for test in reference_tests:
            _inside(snapshot, test.split("::", 1)[0])
        reference = (_run(snapshot, target, reference_tests, out / "reference", project, config)
                     if reference_tests else {"status": "missing", "reference_passed": False})
    defects = [_validate_one(project, target, defect, out / defect["id"], config)
               for defect in target.get("defects", [])]
    result = {"target_id": target["id"], "reference": reference, "defects": defects,
              "valid": bool(reference.get("reference_passed") and reference.get("production_unchanged") and
                            (reference.get("focal") or {}).get("executed") and
                            all(d["eligible"] for d in defects))}
    _json_write(out / "validation.json", result)
    return result


def evaluate_submission(project, target, submission_path, output_dir, config, defects=(), review=None) -> dict:
    """Evaluate exactly one preserved submission; review gates primary metrics.

    `defects` is the fixed inventory of {id,path,old,new,witness}; each definition
    is validated against its witness before evaluating the submitted suite.
    `review` requires the three boolean review keys (plus http_requests for HTTP pilots), and may contain
    defect_attribution={defect_id: true|false} after inspecting mutant failures.
    """
    evaluation_started = time.monotonic()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    submitted = Path(submission_path).resolve() if submission_path else None
    result = {"target_id": target["id"], "test_kind": target.get("test_kind", "unit"),
              "received": bool(submitted and submitted.is_file()),
              "syntax_ok": None, "collected": None, "active_started": None,
              "reference_passed": None, "approval": "not_applicable", "approved": False,
              "coverage_raw": None, "coverage_main": None, "defects": [], "detection_rate": None,
              "review": review, "backend": config.get("backend", "docker")}
    if not result["received"]:
        result["status"] = "no_submission"
        result["total_seconds"] = time.monotonic() - evaluation_started
        _json_write(out / "evaluation.json", result)
        return result
    result["submission_sha256"] = hashlib.sha256(submitted.read_bytes()).hexdigest()
    syntax_error = _syntax(submitted)
    result["syntax_ok"] = syntax_error is None
    if syntax_error:
        result.update(status="syntax_error", error=syntax_error, active_started=False, collected=0,
                      reference_passed=False, approval="rejected")
        result["total_seconds"] = time.monotonic() - evaluation_started
        _json_write(out / "evaluation.json", result)
        return result
    # Copy the submission, so execution always uses the retained bytes rather
    # than a caller-editable file, and no reference tests are co-collected.
    inputs = out / "submission"
    inputs.mkdir(exist_ok=True)
    frozen_submission = inputs / "test_generated.py"
    frozen_submission.write_bytes(submitted.read_bytes())
    with tempfile.TemporaryDirectory(prefix="contextlab-evaluation-") as tmp:
        snapshot = Path(tmp) / "project"
        _copy_project(project, snapshot, exclude=_reserved_paths(project, target))
        _inside(snapshot, target["path"])
        original = _run(snapshot, target, [], out / "original", project, config, frozen_submission)
    result.update({key: original.get(key) for key in
                   ("status", "collected", "active_started", "reference_passed", "seconds",
                    "active_count", "passed_count", "skipped_count", "xfail_count", "failure_categories")})
    result["original"] = original
    result["coverage_raw"] = original.get("focal")
    candidate = bool(original.get("reference_passed") and original.get("production_unchanged") and
                     (original.get("focal") or {}).get("executed"))
    review_keys = _REVIEW_KEYS + (("http_requests",) if target.get("test_kind") == "http" else ())
    review_complete = review is not None and all(review.get(key) is True for key in review_keys)
    rejected_review = review is not None and any(review.get(key) is False for key in review_keys)
    result["approved"] = bool(candidate and review_complete)
    result["approval"] = ("not_applicable" if original["status"] != "completed" else
                          "approved" if result["approved"] else "rejected" if not candidate or rejected_review
                          else "pending_review")
    if result["approved"]:
        result["coverage_main"] = original["focal"]
        for defect in defects:
            defect_out = out / "defects" / defect["id"]
            validation = _validate_one(project, target, defect, defect_out / "validation", config)
            entry = {"id": defect["id"], "eligible": validation["eligible"], "validation": validation,
                     "detected": None, "status": "ineligible"}
            if validation["eligible"]:
                with tempfile.TemporaryDirectory(prefix="contextlab-mutant-") as tmp:
                    mutant = Path(tmp) / "project"
                    _copy_project(project, mutant, exclude=_reserved_paths(project, target))
                    _patch(mutant, defect)
                    run = _run(mutant, target, [], defect_out / "generated", project, config, frozen_submission)
                entry["run"] = run
                if run["status"] != "completed":
                    entry["status"] = run["status"]
                elif run.get("reference_passed"):
                    entry.update(status="survived", detected=False)
                elif (run.get("active_started") and run.get("production_unchanged") and
                      run.get("failure_categories") and
                      set(run["failure_categories"]) <= {"assertion_failure", "execution_error"}):
                    attribution = (review.get("defect_attribution") or {}).get(defect["id"])
                    entry.update(status="detected" if attribution is True else "not_attributed" if attribution is False
                                 else "pending_attribution", detected=attribution)
                else:
                    entry["status"] = "non_behavioral_failure"
            result["defects"].append(entry)
    measured = [d for d in result["defects"] if d["eligible"] and d["detected"] is not None]
    eligible = [d for d in result["defects"] if d["eligible"]]
    result["defects_eligible"] = len(eligible) if result["approved"] else None
    result["defects_measured"] = len(measured) if result["approved"] else None
    result["defects_detected"] = sum(d["detected"] for d in measured) if measured else None
    # Do not turn missing measurements or absent defects into a zero score.
    if eligible and len(measured) == len(eligible):
        result["detection_rate"] = sum(d["detected"] for d in measured) / len(eligible)
    result["detection_complete"] = bool(eligible and len(measured) == len(eligible)) if result["approved"] else None
    result["total_seconds"] = time.monotonic() - evaluation_started
    _json_write(out / "evaluation.json", result)
    return result

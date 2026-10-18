"""Protocol acceptance checks, independent of adapters and providers.

These tests exercise forbidden information and focal coverage, rather than
asserting the harness' internal representation of ordinary successful runs.
"""
from pathlib import Path

import coverage
import pytest

from contextlab.context import ContextError, build_context
from contextlab.pytest_plugin import focal_body_lines, focal_coverage


def _project(root: Path):
    return {"root": str(root), "include": ["**/*.py", "docs/regras.md"],
            "source_roots": ["."]}


def _write(root: Path, path: str, text: str):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def test_autonomous_has_no_reserved_tests_instructions_or_symlink(tmp_path):
    _write(tmp_path, "pkg/core.py", "def focal(x):\n    return x + 1\n")
    _write(tmp_path, "tests/test_secret.py", "EXPECTED_SECRET = 123456\n")
    _write(tmp_path, ".git/private.py", "HISTORY_SECRET = 987654\n")
    _write(tmp_path, "docs/regras.md", "Teste reservado:\n```python\ndef test_case():\n    assert True\n```\n")
    _write(tmp_path, "pkg/AGENTS.md", "Hidden instruction\n")
    outside = tmp_path.parent / (tmp_path.name + "-outside.py")
    outside.write_text("EXTERNAL_SECRET = 'do not expose'\n", encoding="utf-8")
    (tmp_path / "pkg/escape.py").symlink_to(outside)
    result = build_context(_project(tmp_path), {"path": "pkg/core.py", "symbol": "focal"}, "A", 5000)
    assert result["text"] == ""  # A obtains code only through its later reads.
    assert set(result["files"]) == {"pkg/core.py"}
    serialized = "\n".join(result["files"].values())
    assert "123456" not in serialized and "987654" not in serialized
    assert "EXTERNAL_SECRET" not in serialized


def test_local_over_budget_is_rejected_instead_of_cut(tmp_path):
    source = "def focal(x):\n    \"\"\"" + "explanation " * 100 + "\"\"\"\n    return x\n"
    _write(tmp_path, "core.py", source)
    for condition in ("L", "R"):
        with pytest.raises(ContextError, match="Integral L"):
            build_context(_project(tmp_path), {"path": "core.py", "symbol": "focal"}, condition, 100)


def test_recovered_does_not_expand_dependency_of_dependency(tmp_path):
    _write(tmp_path, "core.py", "from helper import direct\n\ndef focal(x):\n    return direct(x)\n")
    _write(tmp_path, "helper.py", "from private_data import OFFSET\n\ndef direct(x):\n    return x + OFFSET\n")
    _write(tmp_path, "private_data.py", "OFFSET = 87654321\n")
    project = _project(tmp_path)
    target = {"path": "core.py", "symbol": "focal"}
    local = build_context(project, target, "L", 5000)
    recovered = build_context(project, target, "R", 5000)
    assert recovered["text"].startswith(local["text"])
    assert "def direct(x):" in recovered["text"]
    assert "OFFSET = 87654321" not in recovered["text"]
    assert recovered == build_context(project, target, "R", 5000)


def test_focal_metric_excludes_nested_function_body(tmp_path):
    source = "def focal(x):\n    def nested(y):\n        if y:\n            return 10\n        return 20\n    if x:\n        return nested(x)\n    return 0\n"
    path = tmp_path / "core.py"
    path.write_text(source, encoding="utf-8")
    cov = coverage.Coverage(branch=True, config_file=False, data_file=None)
    cov.start()
    scope = {}
    exec(compile(source, str(path), "exec"), scope)
    scope["focal"](True)
    cov.stop()
    focal = focal_coverage(cov, path, "focal")
    assert not set(range(2, 6)) & set(focal["executable_lines"])
    assert focal["branch_total"] == 2  # Only the focal `if`, not the nested `if`.
    assert focal["branch_covered"] == 1
    assert focal["line_covered"] == 2
    assert focal["line_total"] == 3


def test_fixture_cannot_be_relabelled_as_pilot(tmp_path):
    import json
    from contextlab.manifest import ManifestError, load_config

    configuration = {
        "schema_version": 1, "phase": "pilot", "seed": 1,
        "repetitions": 1, "conditions": ["L"],
        "limits": {"context_chars": 1000, "tool_calls": 5,
                   "generation_seconds": 10, "evaluation_seconds": 10},
        "evaluation": {"backend": "local"},
        "agents": [{"id": "pretend_real", "kind": "fixture", "fixture_dir": "fixtures"}],
        "projects": [],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(configuration), encoding="utf-8")
    with pytest.raises(ManifestError, match="Fixtures autorais"):
        load_config(path)


def test_source_change_invalidates_frozen_experiment(tmp_path):
    from contextlab.manifest import ManifestError, freeze, load_lock

    _write(tmp_path, "core.py", "def focal(x):\n    return x + 1\n")
    _write(tmp_path, "reference/test_core.py", "def test_focal():\n    assert True\n")
    project = _project(tmp_path) | {
        "id": "project", "evaluation_include": ["**/*.py"],
        "targets": [{"id": "focal", "path": "core.py", "symbol": "focal"}],
    }
    config = {"phase": "demo", "seed": 1, "repetitions": 1,
              "conditions": ["L", "R", "A"],
              "agents": [{"id": "demo", "kind": "fixture"}], "projects": [project],
              "evaluation": {"backend": "local"}}
    lock_path = tmp_path / "lock.json"
    frozen = freeze(config, lock_path)
    assert len(frozen["plan"]) == 3
    assert load_lock(lock_path)["lock_hash"] == frozen["lock_hash"]
    _write(tmp_path, "core.py", "def focal(x):\n    return x + 2\n")
    with pytest.raises(ManifestError, match="arquivos mudaram"):
        load_lock(lock_path)


def test_main_gate_rejects_pilot_with_only_evaluation_infrastructure_failures(tmp_path, monkeypatch):
    import json
    from contextlab import adapters, manifest, runner
    from contextlab.manifest import ManifestError, digest, implementation_hash, plan, snapshot

    agents = [{"id": "codex", "kind": "codex", "model": "fixed-codex"}]
    limits = {"context_chars": 10000, "tool_calls": 10, "generation_seconds": 30,
              "evaluation_seconds": 10}
    project_root = tmp_path / "main_project"
    _write(project_root, "core.py", "def focal(x):\n    return x\n")
    project = _project(project_root) | {"id": "project", "evaluation_include": ["**/*.py"],
                                        "targets": [{"id": "f", "path": "core.py", "symbol": "focal"}]}
    config = {"phase": "main", "projects": [project], "agents": agents, "conditions": ["L", "R", "A"],
              "seed": 1, "repetitions": 3, "limits": limits,
              "evaluation": {"backend": "docker", "image": "contextlab:test"}}
    pilot = {**config, "phase": "pilot", "repetitions": 1,
             "projects": [{**project, "root": str(tmp_path / "different_pilot_project")}]}
    pilot_dir = tmp_path / "pilot"
    pilot_dir.mkdir()
    runtime = {"python": "test", "evaluation_image_id": "sha256:test"}
    header = {"config": pilot, "plan": plan(pilot), "runtime": runtime,
              "implementation_hash": implementation_hash()}
    (pilot_dir / "run.json").write_text(json.dumps(header), encoding="utf-8")
    for row in header["plan"]:
        path = pilot_dir / row["id"] / "record.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"status": "finished", "generation": {"status": "completed", "version": "1"},
                                    "evaluation": {"status": "infrastructure_error"}}), encoding="utf-8")
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()
    validation = {"config_hash": digest(config), "source_hashes": snapshot(config),
                  "runtime": runtime, "implementation_hash": implementation_hash(),
                  "targets": {"project__f": {"valid": True}}}
    (validation_dir / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
    monkeypatch.setattr(adapters, "doctor_agent", lambda agent: {"ready": True, "version": "1"})
    monkeypatch.setattr(manifest, "runtime_fingerprint", lambda config: runtime)
    monkeypatch.setattr(runner, "runtime_fingerprint", lambda config: runtime, raising=False)
    evidence = {"pilot_run": str(pilot_dir), "validation_dir": str(validation_dir),
                "agent_versions": {"codex": "1"}}
    with pytest.raises(ManifestError, match="Piloto|piloto|avaliação"):
        runner.check_main_evidence(config, evidence)

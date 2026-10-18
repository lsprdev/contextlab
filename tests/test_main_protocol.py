"""Acceptance checks for the 108-generation protocol; no model calls."""
import json
from collections import Counter

import pytest

from contextlab import adapters, manifest, runner
from contextlab.manifest import ManifestError, load_config, plan


def make_manifest(tmp_path, projects=4, targets=3):
    configuration = {
        "schema_version": 1, "phase": "main", "seed": 42,
        "repetitions": 3, "conditions": ["L", "R", "A"],
        "agents": [{"id": "codex", "kind": "codex", "model": "fixed-model"}],
        "limits": {"context_chars": 10000, "tool_calls": 10,
                   "generation_seconds": 30, "evaluation_seconds": 10},
        "evaluation": {"backend": "docker", "image": "contextlab:test"},
        "projects": [],
    }
    for project_index in range(projects):
        root = tmp_path / f"project_{project_index}"
        (root / "reference").mkdir(parents=True)
        (root / "core.py").write_text("\n".join(
            f"def focal_{i}(value):\n    return value + {i}\n" for i in range(targets)
        ), encoding="utf-8")
        (root / "reference/test_core.py").write_text("\n".join(
            f"from core import focal_{i}\ndef test_focal_{i}():\n    assert focal_{i}(0) == {i}\n"
            for i in range(targets)
        ), encoding="utf-8")
        configuration["projects"].append({
            "id": root.name, "root": str(root), "source_roots": ["."],
            "include": ["core.py"], "evaluation_include": ["core.py", "reference/*.py"],
            "targets": [{"id": f"focal_{i}", "path": "core.py", "symbol": f"focal_{i}",
                         "import": f"core:focal_{i}",
                         "reference_tests": [f"reference/test_core.py::test_focal_{i}"]}
                        for i in range(targets)],
        })
    return configuration


def load_manifest(tmp_path, configuration):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(configuration), encoding="utf-8")
    return load_config(path)


@pytest.fixture
def main_config(tmp_path):
    return load_manifest(tmp_path, make_manifest(tmp_path))


def test_main_has_108_unique_paired_generations(main_config):
    rows = plan(main_config)
    assert len(rows) == len({row["id"] for row in rows}) == 108
    assert {row["agent"] for row in rows} == {"codex"}
    assert Counter(row["condition"] for row in rows) == {"L": 36, "R": 36, "A": 36}
    assert set(Counter(row["project"] for row in rows).values()) == {27}
    per_target = Counter((row["project"], row["target"]) for row in rows)
    assert len(per_target) == 12 and set(per_target.values()) == {9}
    expected_targets = set(per_target)
    for condition in ("L", "R", "A"):
        for repetition in (1, 2, 3):
            assert {(row["project"], row["target"]) for row in rows
                    if row["condition"] == condition and row["repetition"] == repetition} == expected_targets


def test_main_randomizes_complete_blocks_reproducibly(main_config):
    rows = plan(main_config)
    assert rows == plan(main_config)
    assert [row["order"] for row in rows] == list(range(1, 109))
    for offset in range(0, len(rows), 3):
        block = rows[offset:offset + 3]
        assert len({(row["project"], row["target"], row["repetition"]) for row in block}) == 1
        assert {row["condition"] for row in block} == {"L", "R", "A"}
    other = plan({**main_config, "seed": 123})
    assert [row["id"] for row in rows] != [row["id"] for row in other]
    assert {row["id"] for row in rows} == {row["id"] for row in other}


@pytest.mark.parametrize("projects,targets,kinds,repetitions", [
    (2, 6, ["codex", "claude"], 3),  # Superseded 216-generation protocol.
    (4, 3, ["codex", "claude"], 2),  # Superseded 144-generation protocol.
    (4, 3, ["codex"], 2),
    (4, 3, ["claude"], 3),
    (4, 3, ["codex", "codex"], 3),
    (3, 4, ["codex"], 3),  # Same total, wrong project/function allocation.
])
def test_main_rejects_other_designs(tmp_path, projects, targets, kinds, repetitions):
    configuration = make_manifest(tmp_path, projects, targets)
    configuration["agents"] = [{"id": f"agent_{i}", "kind": kind, "model": f"model_{i}"}
                               for i, kind in enumerate(kinds)]
    configuration["repetitions"] = repetitions
    with pytest.raises(ManifestError, match="108 gerações"):
        load_manifest(tmp_path, configuration)


def test_main_still_requires_all_strategies_and_docker(tmp_path, main_config):
    with pytest.raises(ManifestError, match="108 gerações"):
        load_manifest(tmp_path, {**main_config, "conditions": ["L", "R"]})
    with pytest.raises(ManifestError, match="avaliação Docker"):
        load_manifest(tmp_path, {**main_config, "evaluation": {"backend": "local"}})


@pytest.fixture
def main_evidence(tmp_path, main_config, monkeypatch):
    """Synthetic pilot/validation records test gates, not experimental results."""
    runtime = {"python": "test", "evaluation_image_id": "sha256:test"}
    monkeypatch.setattr(manifest, "runtime_fingerprint", lambda config: dict(runtime))
    monkeypatch.setattr(runner, "runtime_fingerprint", lambda config: dict(runtime))
    monkeypatch.setattr(adapters, "doctor_agent", lambda agent: {"ready": True, "version": "test-version"})
    pilot = make_manifest(tmp_path / "external_pilot", projects=1, targets=1)
    pilot.update(phase="pilot", repetitions=1)
    pilot_dir = tmp_path / "pilot"
    header = {"config": pilot, "plan": plan(pilot), "runtime": runtime,
              "implementation_hash": manifest.implementation_hash()}
    manifest.write_json(pilot_dir / "run.json", header)
    for row in header["plan"]:
        manifest.write_json(pilot_dir / row["id"] / "record.json", {
            "status": "finished", "generation": {"status": "completed", "version": "test-version"},
            "evaluation": {"status": "completed", "approval": "rejected"},
        })
    validation_dir = tmp_path / "validation"
    manifest.write_json(validation_dir / "validation.json", {
        "config_hash": manifest.digest(main_config), "source_hashes": manifest.snapshot(main_config),
        "runtime": runtime, "implementation_hash": manifest.implementation_hash(),
        "targets": {f"{p['id']}__{t['id']}": {"valid": True}
                    for p in main_config["projects"] for t in p["targets"]},
    })
    evidence = {"pilot_run": str(pilot_dir), "validation_dir": str(validation_dir),
                "agent_versions": {"codex": "test-version"}, "reviewer": "test-reviewer",
                "isolation_verified": True, "docs_sanitized": True,
                "focal_mapping_verified": True, "budget_calibrated": True}
    return evidence, pilot_dir, header


def test_main_accepts_codex_only_pilot_and_freezes_108(main_config, main_evidence, tmp_path):
    evidence, _, _ = main_evidence
    runner.check_main_evidence(main_config, evidence)
    assert evidence["pilot_record_hash"] and evidence["validation_hash"]
    lock_path = tmp_path / "main.lock.json"
    manifest.freeze(main_config, lock_path, evidence)
    assert len(manifest.load_lock(lock_path)["plan"]) == 108


@pytest.mark.parametrize("missing_condition", ["L", "R", "A"])
def test_main_requires_completed_codex_pilot_in_each_strategy(main_config, main_evidence, missing_condition):
    evidence, pilot_dir, header = main_evidence
    row = next(row for row in header["plan"] if row["condition"] == missing_condition)
    (pilot_dir / row["id"] / "record.json").unlink()
    with pytest.raises(ManifestError, match="Codex nas três condições"):
        runner.check_main_evidence(main_config, evidence)


def test_main_rejects_pilot_with_different_model(main_config, main_evidence):
    evidence, pilot_dir, header = main_evidence
    header["config"]["agents"][0]["model"] = "other-model"
    manifest.write_json(pilot_dir / "run.json", header)
    with pytest.raises(ManifestError, match="Modelos da coleta"):
        runner.check_main_evidence(main_config, evidence)

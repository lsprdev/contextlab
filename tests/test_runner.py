import json
from pathlib import Path

import pytest

from contextlab.manifest import ManifestError, freeze, load_config, load_lock, plan
from contextlab.runner import execute, extract_submission, review_trajectory


DEMO = Path(__file__).parents[1] / "examples/demo.json"


def test_generic_pilot_can_plan_multiple_agents_for_future_work():
    config = load_config(DEMO)
    config["phase"] = "pilot"
    config["agents"] = [{"id": "codex", "kind": "codex"}, {"id": "claude", "kind": "claude"}]
    config["repetitions"] = 3
    rows = plan(config)
    assert len(rows) == 36
    assert rows == plan(config)
    for agent in ("codex", "claude"):
        for condition in ("L", "R", "A"):
            assert {(r["project"], r["target"]) for r in rows if r["agent"] == agent and r["condition"] == condition} == {
                ("loja", "frete"), ("agenda", "preco")}


@pytest.mark.parametrize("response", ["```python\ndef a(): pass\n```\n```python\ndef b(): pass\n```",
                                     "Texto\n```python\na=1\n```", ""])
def test_extraction_does_not_choose_or_repair(response):
    with pytest.raises(ValueError):
        extract_submission(response)


def test_extraction_preserves_raw_invalid_python_for_evaluation():
    source = "def test_bad(:\n"
    assert extract_submission(source) == source


def test_resume_never_regenerates_completed_attempt(tmp_path, monkeypatch):
    config = load_config(DEMO)
    lock = tmp_path / "demo.lock.json"
    freeze(config, lock)
    import contextlab.evaluation
    monkeypatch.setattr(contextlab.evaluation, "evaluate_submission", lambda *a, **k: {"status": "completed"})
    destination = tmp_path / "run"
    execute(lock, destination, trusted_local=True, max_runs=1)
    row = plan(config)[0]
    record = (destination / row["id"] / "record.json").read_bytes()
    response = (destination / row["id"] / "response.txt").read_bytes()
    execute(lock, destination, trusted_local=True, resume=True, max_runs=1)
    assert (destination / row["id"] / "record.json").read_bytes() == record
    assert (destination / row["id"] / "response.txt").read_bytes() == response
    assert len(list(destination.glob("*/record.json"))) == 2


def test_lock_tampering_is_detected(tmp_path):
    config = load_config(DEMO)
    lock = tmp_path / "demo.lock.json"
    data = freeze(config, lock)
    data["plan"][0]["condition"] = "A"
    lock.write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="Lock foi alterado"):
        load_lock(lock)


def test_native_generation_cannot_use_local_evaluation(tmp_path):
    config = load_config(DEMO)
    config["phase"] = "pilot"
    from contextlab.runner import evaluation_config
    with pytest.raises(ManifestError, match="somente para demo"):
        evaluation_config(config, True)


def test_same_run_cannot_execute_concurrently(tmp_path):
    import fcntl
    guard = tmp_path / "run.execution.lock"
    with guard.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ManifestError, match="já está em andamento"):
            execute(tmp_path / "unused.lock.json", tmp_path / "run", resume=True)


@pytest.fixture
def frozen_review(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from contextlab import evaluation, manifest

    config = load_config(DEMO)
    config["evaluation"]["backend"] = "docker"
    runtime = {"python": "3.12.11", "pytest": "8.4.2", "coverage": "7.10.7",
               "evaluation_image_id": "sha256:original"}
    monkeypatch.setattr(manifest, "runtime_fingerprint", lambda config: dict(runtime))
    evaluator = Mock(return_value={"status": "completed", "approval": "pending_review"})
    monkeypatch.setattr(evaluation, "evaluate_submission", evaluator)
    lock = tmp_path / "demo.lock.json"
    freeze(config, lock)
    output = tmp_path / "run"
    execute(lock, output, max_runs=1)
    evaluator.reset_mock()
    return output / plan(config)[0]["id"], runtime, evaluator


def test_review_rejects_changed_implementation_before_evaluation(frozen_review, monkeypatch):
    from contextlab import manifest
    path, _, evaluator = frozen_review
    monkeypatch.setattr(manifest, "implementation_hash", lambda: "changed-implementation")
    with pytest.raises(ManifestError, match="Código do ContextLab mudou"):
        review_trajectory(path, "test-reviewer", {})
    evaluator.assert_not_called()
    assert not (path / "reviews").exists()


@pytest.mark.parametrize("component", ["python", "pytest", "coverage", "evaluation_image_id"])
def test_review_rejects_changed_runtime_before_evaluation(frozen_review, component):
    path, runtime, evaluator = frozen_review
    runtime[component] = "changed"
    with pytest.raises(ManifestError, match="Python, dependências ou imagem Docker mudaram"):
        review_trajectory(path, "test-reviewer", {})
    evaluator.assert_not_called()
    assert not (path / "reviews").exists()


def test_review_rejects_modified_header_or_record_lock(frozen_review):
    path, _, evaluator = frozen_review
    header_path = path.parent / "run.json"
    original = header_path.read_text()
    header = json.loads(original)
    header["config"]["limits"]["context_chars"] += 1
    header_path.write_text(json.dumps(header))
    with pytest.raises(ManifestError, match="Lock foi alterado"):
        review_trajectory(path, "test-reviewer", {})
    header_path.write_text(original)
    record_path = path / "record.json"
    record = json.loads(record_path.read_text())
    record["lock_hash"] = "other-lock"
    record_path.write_text(json.dumps(record))
    with pytest.raises(ManifestError, match="outro protocolo"):
        review_trajectory(path, "test-reviewer", {})
    evaluator.assert_not_called()


def test_review_preserves_original_evaluation_and_appends_history(frozen_review):
    path, _, evaluator = frozen_review
    original = json.loads((path / "record.json").read_text())["evaluation"]
    evaluator.return_value = {"status": "completed", "approval": "rejected"}
    decisions = {"behavioral_assertions": False, "no_target_mock": True, "no_production_changes": True}
    review_trajectory(path, "test-reviewer", decisions)
    review_trajectory(path, "test-reviewer", decisions)
    record = json.loads((path / "record.json").read_text())
    assert record["evaluation"] == original
    assert record["reviewed_evaluation"]["approval"] == "rejected"
    assert len(list((path / "reviews").glob("review-*.json"))) == 2
    assert evaluator.call_count == 2

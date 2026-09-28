import json
from pathlib import Path

import pytest

from contextlab.manifest import ManifestError, freeze, load_config, load_lock, plan
from contextlab.runner import execute, extract_submission


DEMO = Path(__file__).parents[1] / "examples/demo.json"


def test_paired_matrix_uses_same_targets_in_every_condition():
    config = load_config(DEMO)
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

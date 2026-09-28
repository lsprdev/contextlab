from pathlib import Path

import pytest

from contextlab.evaluation import evaluate_submission, validate_defects
from contextlab.pytest_plugin import focal_body_lines

REVIEW = {"behavioral_assertions": True, "no_target_mock": True, "no_production_changes": True}
CONFIG = {"backend": "local", "trusted_local": True, "timeout_seconds": 10}
SOURCE = '''def price(value):
    if value <= 5:
        return value * 2
    return value + 1
'''


@pytest.fixture
def fixture_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "product.py").write_text(SOURCE)
    (root / "reference").mkdir()
    (root / "reference" / "test_reference.py").write_text(
        "from product import price\ndef test_boundary():\n    assert price(5) == 10\n")
    target = {"id": "price", "path": "product.py", "symbol": "price", "import": "product:price",
              "reference_tests": ["reference/test_reference.py"], "defects": [
                  {"id": "boundary", "path": "product.py", "old": "value <= 5", "new": "value < 5",
                   "witness": "reference/test_reference.py::test_boundary"}]}
    return {"id": "example", "root": str(root), "source_roots": ["."]}, target


def run(tmp_path, fixture_project, source, review=REVIEW, **kwargs):
    submission = tmp_path / "suite.py"
    submission.write_text(source)
    project, target = fixture_project
    return evaluate_submission(project, target, submission, tmp_path / "results", CONFIG,
                               review=review, **kwargs)


def test_success_requires_review_and_focal_branch_counts(tmp_path, fixture_project):
    result = run(tmp_path, fixture_project,
                 "from product import price\ndef test_low():\n    assert price(2) == 4\n", review=None)
    assert result["active_started"] is True
    assert result["reference_passed"] is True
    assert result["approval"] == "pending_review"
    assert result["coverage_main"] is None
    assert result["coverage_raw"]["branch_total"] == 2
    assert result["coverage_raw"]["branch_covered"] == 1
    assert result["coverage_raw"]["line_total"] == 3
    assert result["coverage_raw"]["line_covered"] == 2
    assert result["total_seconds"] >= result["original"]["seconds"] > 0


def test_reviewed_full_coverage_and_no_defects_is_not_zero(tmp_path, fixture_project):
    result = run(tmp_path, fixture_project,
                 "from product import price\ndef test_values():\n    assert price(2) == 4\n    assert price(9) == 10\n")
    assert result["approved"] is True
    assert result["coverage_main"]["branch_rate"] == 1
    assert result["detection_rate"] is None
    assert result["defects_eligible"] == 0


@pytest.mark.parametrize("source,category,active", [
    ("def test_syntax(:\n", "syntax_error", False),
    ("import nonexistent_library\ndef test_x():\n    assert True\n", "collection_error", False),
    ("import pytest\n@pytest.fixture\ndef bad():\n    raise ValueError('setup')\ndef test_x(bad):\n    assert True\n", "setup_error", False),
    ("from product import price\ndef test_x():\n    assert price(5) == 0\n", "assertion_failure", True),
    ("from product import price\ndef test_x():\n    price(None)\n", "execution_error", True),
])
def test_failure_categories_are_distinct(tmp_path, fixture_project, source, category, active):
    result = run(tmp_path, fixture_project, source)
    assert result["active_started"] is active
    assert result["total_seconds"] > 0
    assert result["coverage_main"] is None
    assert not result["approved"]
    assert result["status"] == category if category == "syntax_error" else category in result["failure_categories"]


@pytest.mark.parametrize("source", [
    "from product import price\ndef test_nothing():\n    assert True\n",
    "def test_import_only():\n    from product import price\n    assert callable(price)\n",
    "import pytest\nfrom product import price\n@pytest.mark.skip\ndef test_skip():\n    assert price(5) == 10\n",
    "import pytest\nfrom product import price\n@pytest.mark.xfail\ndef test_expected():\n    assert price(5) == 0\n",
    "import pytest\nfrom product import price\n@pytest.mark.xfail\ndef test_unexpected_pass():\n    assert price(5) == 10\n",
])
def test_import_only_skip_and_xfail_do_not_approve(tmp_path, fixture_project, source):
    result = run(tmp_path, fixture_project, source)
    assert not result["approved"]
    assert result["coverage_main"] is None


def test_nested_definition_body_is_excluded(tmp_path, fixture_project):
    project, target = fixture_project
    Path(project["root"], "product.py").write_text(
        "def price(value):\n    def inner(x):\n        if x:\n            return 10\n        return 20\n    return inner(value)\n")
    result = run(tmp_path, fixture_project,
                 "from product import price\ndef test_nested():\n    assert price(1) == 10\n")
    assert result["coverage_main"]["executable_lines"] == [6]
    assert result["coverage_main"]["line_rate"] == 1
    assert result["coverage_main"]["branch_rate"] is None


def test_same_line_focal_body_explicitly_unsupported():
    with pytest.raises(ValueError, match="One-line"):
        focal_body_lines("def price(value): return value\n", "price")


def test_changed_production_is_rejected(tmp_path, fixture_project):
    result = run(tmp_path, fixture_project,
                 "import product\nfrom pathlib import Path\ndef test_changes():\n    assert product.price(2) == 4\n    Path(product.__file__).write_text('# changed')\n")
    assert result["original"]["production_unchanged"] is False
    assert not result["approved"]


def test_fixed_defect_validation_and_attribution(tmp_path, fixture_project):
    project, target = fixture_project
    validation = validate_defects(project, target, tmp_path / "validation", CONFIG)
    assert validation["valid"]
    assert validation["defects"][0]["eligible"]
    review = dict(REVIEW, defect_attribution={"boundary": True})
    result = run(tmp_path, fixture_project,
                 "from product import price\ndef test_boundary():\n    assert price(5) == 10\n",
                 review=review, defects=target["defects"])
    assert result["approved"]
    assert result["defects"][0]["status"] == "detected"
    assert result["detection_rate"] == 1
    assert result["detection_complete"] is True
    entry = result["defects"][0]
    subprocess_seconds = (result["original"]["seconds"] + entry["validation"]["baseline"]["seconds"] +
                          entry["validation"]["mutated"]["seconds"] + entry["run"]["seconds"])
    assert result["total_seconds"] >= subprocess_seconds > 0
    assert Path(project["root"], "product.py").read_text() == SOURCE


def test_mutant_assertion_waits_for_attribution(tmp_path, fixture_project):
    result = run(tmp_path, fixture_project,
                 "from product import price\ndef test_boundary():\n    assert price(5) == 10\n",
                 defects=fixture_project[1]["defects"])
    assert result["defects"][0]["status"] == "pending_attribution"
    assert result["detection_rate"] is None
    assert result["defects_measured"] == 0


def test_surviving_mutant_is_real_zero(tmp_path, fixture_project):
    result = run(tmp_path, fixture_project,
                 "from product import price\ndef test_non_boundary():\n    assert price(2) == 4\n",
                 defects=fixture_project[1]["defects"])
    assert result["defects"][0]["status"] == "survived"
    assert result["detection_rate"] == 0


def test_timeout_is_not_detection(tmp_path, fixture_project):
    project, target = fixture_project
    path = tmp_path / "infinite.py"
    path.write_text("def test_loop():\n    while True:\n        pass\n")
    result = evaluate_submission(project, target, path, tmp_path / "results",
                                 dict(CONFIG, timeout_seconds=1), review=REVIEW, defects=target["defects"])
    assert result["status"] == "timeout"
    assert result["approval"] == "not_applicable"
    assert result["detection_rate"] is None


def test_local_backend_requires_explicit_trust(tmp_path, fixture_project):
    project, target = fixture_project
    path = tmp_path / "suite.py"
    path.write_text("def test_ok():\n    assert True\n")
    with pytest.raises(ValueError, match="trusted_local"):
        evaluate_submission(project, target, path, tmp_path / "results", {"backend": "local"})


def test_xfail_cannot_supply_target_coverage_for_empty_active_test(tmp_path, fixture_project):
    result = run(tmp_path, fixture_project,
        "import pytest\nfrom product import price\n@pytest.mark.xfail\ndef test_expected():\n    assert price(5) == 0\ndef test_empty():\n    assert True\n")
    assert result["active_started"] is True
    assert result["reference_passed"] is True
    assert result["coverage_raw"]["executed"] is False
    assert result["approved"] is False


def test_runtime_mutant_failure_can_be_manually_attributed(tmp_path, fixture_project):
    project, target = fixture_project
    defect = {"id": "zero_division", "path": "product.py", "old": "return value * 2",
              "new": "return value / 0", "witness": "reference/test_reference.py::test_boundary"}
    result = run(tmp_path, fixture_project,
                 "from product import price\ndef test_boundary():\n    assert price(5) == 10\n",
                 review=dict(REVIEW, defect_attribution={"zero_division": True}), defects=[defect])
    assert result["defects"][0]["status"] == "detected"
    assert result["detection_rate"] == 1


def test_reserved_reference_cannot_be_imported_by_generated_test(tmp_path, fixture_project):
    result = run(tmp_path, fixture_project,
                 "from reference.test_reference import test_boundary\n")
    assert result["status"] == "completed"
    assert result["failure_categories"] == ["collection_error"]
    assert result["approved"] is False


def test_docker_command_enforces_boundary_without_network_or_host_secrets(tmp_path, fixture_project, monkeypatch):
    import json
    from contextlab import evaluation

    captured = {}

    class DockerProcess:
        def __init__(self, command, **kwargs):
            captured["command"] = command
            mounts = [command[index + 1] for index, value in enumerate(command) if value == "--mount"]
            project_mount = next(m for m in mounts if "dst=/project," in m)
            project_path = Path(project_mount.split("src=", 1)[1].split(",", 1)[0])
            assert not (project_path / "reference/test_reference.py").exists()
            results_mount = next(m for m in mounts if "dst=/results" in m)
            results_path = Path(results_mount.split("src=", 1)[1].split(",", 1)[0])
            (results_path / "pytest_report.json").write_text(json.dumps({
                "exit_code": 0, "collected": 1, "collection_errors": [], "focal": {"executed": True},
                "reports": [{"nodeid": "suite::test", "when": "call", "outcome": "passed",
                             "expected_failure": False, "assertion_failure": False}]}))

        def wait(self, timeout):
            return 0

    monkeypatch.setattr(evaluation.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(evaluation.subprocess, "Popen", DockerProcess)
    project, target = fixture_project
    source = tmp_path / "generated.py"
    source.write_text("from product import price\ndef test_price():\n    assert price(5) == 10\n")
    result = evaluate_submission(project, target, source, tmp_path / "results", {"backend": "docker"})
    command = captured["command"]
    for flag in ["--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                 "--pids-limit=128", "--memory=1g", "--cpus=1"]:
        assert flag in command
    mounts = [command[index + 1] for index, value in enumerate(command) if value == "--mount"]
    assert all("readonly" in mount for mount in mounts if "dst=/results" not in mount)
    assert "--user" in command
    assert not any("API_KEY" in value or "auth.json" in value or "docker.sock" in value for value in command)
    assert result["approval"] == "pending_review"


def test_missing_docker_never_falls_back_to_local(tmp_path, fixture_project, monkeypatch):
    from contextlab import evaluation
    monkeypatch.setattr(evaluation.shutil, "which", lambda name: None)
    project, target = fixture_project
    source = tmp_path / "generated.py"
    source.write_text("def test_ok():\n    assert True\n")
    result = evaluate_submission(project, target, source, tmp_path / "results", {})
    assert result["status"] == "infrastructure_error"
    assert result["approval"] == "not_applicable"
    assert result["original"]["error"] == "Docker executable unavailable"


def test_absent_submission_records_total_duration(tmp_path, fixture_project):
    import json
    project, target = fixture_project
    result = evaluate_submission(project, target, None, tmp_path / "results", CONFIG)
    assert result["status"] == "no_submission"
    assert result["total_seconds"] > 0
    saved = json.loads((tmp_path / "results/evaluation.json").read_text())
    assert saved["total_seconds"] == result["total_seconds"]


def test_keyboard_interrupt_kills_group_reaps_child_and_removes_docker(tmp_path, fixture_project, monkeypatch):
    import signal
    from types import SimpleNamespace
    from contextlab import evaluation

    events = []
    captured = {}

    class InterruptedDockerProcess:
        pid = 54321

        def __init__(self, command, **kwargs):
            captured["container"] = command[command.index("--name") + 1]
            self.waits = 0

        def wait(self, timeout):
            self.waits += 1
            events.append(("wait", timeout))
            if self.waits == 1:
                raise KeyboardInterrupt
            return -9

    def remove_container(command, **kwargs):
        events.append(("docker_remove", command))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(evaluation.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(evaluation.subprocess, "Popen", InterruptedDockerProcess)
    monkeypatch.setattr(evaluation.subprocess, "run", remove_container)
    monkeypatch.setattr(evaluation.os, "killpg", lambda pid, sig: events.append(("killpg", pid, sig)))
    project, target = fixture_project
    source = tmp_path / "generated.py"
    source.write_text("def test_ok():\n    assert True\n")
    with pytest.raises(KeyboardInterrupt):
        evaluate_submission(project, target, source, tmp_path / "results", {"backend": "docker"})
    assert events == [("wait", 30.0), ("killpg", 54321, signal.SIGKILL), ("wait", 5),
                      ("docker_remove", ["docker", "rm", "-f", captured["container"]])]
    assert not (tmp_path / "results/evaluation.json").exists()

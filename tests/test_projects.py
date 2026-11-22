import json
from pathlib import Path

import pytest

from contextlab.cli import main
from contextlab.manifest import ManifestError
from contextlab.projects import attempts, find_attempt, project_folder, read_project


@pytest.fixture
def project(tmp_path, monkeypatch):
    folder = tmp_path / "projects/simples"
    for name in ("src", "tests", "tutorial"):
        (folder / name).mkdir(parents=True)
    (folder / "src/calculo.py").write_text("def somar(a, b):\n    return a + b\n")
    source = "from calculo import somar\n\ndef test_soma():\n    assert somar(2, 3) == 5\n"
    (folder / "tests/test_calculo.py").write_text(source)
    (folder / "tutorial/simples__somar.py").write_text(source)
    monkeypatch.chdir(tmp_path)
    return folder


def register():
    return main(["create", "simples", "--target", "src/calculo.py:somar",
                 "--reference", "tests/test_calculo.py", "--mode", "demo",
                 "--conditions", "L", "--repetitions", "1"])


def test_create_links_project_function_and_sources_without_overwriting(project):
    assert register() == 0
    saved = (project / "contextlab.json").read_bytes()
    config = read_project(project)
    unit = config["projects"][0]
    assert unit["targets"][0]["import"] == "calculo:somar"
    assert unit["include"] == ["src/calculo.py"]
    assert "tests/test_calculo.py" in unit["evaluation_include"]
    assert "tutorial/simples__somar.py" not in unit["evaluation_include"]
    assert register() == 2
    assert (project / "contextlab.json").read_bytes() == saved


def test_create_invalid_reference_leaves_no_config(project):
    assert main(["create", "simples", "--target", "src/calculo.py:somar",
                 "--reference", "tests/ausente.py", "--mode", "demo",
                 "--conditions", "L", "--repetitions", "1"]) == 2
    assert not (project / "contextlab.json").exists()


def test_create_accepts_private_function_name(project):
    (project / "src/calculo.py").write_text("def _somar(a, b):\n    return a + b\n")
    (project / "tutorial/simples__alvo_somar.py").write_text(
        "from calculo import _somar\n\ndef test_soma():\n    assert _somar(2, 3) == 5\n")
    assert main(["create", "simples", "--target", "src/calculo.py:_somar",
                 "--reference", "tests/test_calculo.py", "--mode", "demo",
                 "--conditions", "L", "--repetitions", "1"]) == 0
    target = read_project(project)["projects"][0]["targets"][0]
    assert target["symbol"] == "_somar"
    assert target["import"] == "calculo:_somar"


def test_lookup_from_subdirectory_and_name_validation(project, monkeypatch):
    monkeypatch.chdir(project / "src")
    assert project_folder("simples") == project
    for name in ("../simples", "run", "/tmp", "Com Espaço"):
        with pytest.raises(ManifestError):
            project_folder(name)


def test_rejects_symlink_to_other_project(project):
    (project.parent / "atalho").symlink_to(project, target_is_directory=True)
    with pytest.raises(ManifestError, match="simbólico"):
        project_folder("atalho")


def test_configure_updates_plan_and_keeps_previous_when_invalid(project):
    assert register() == 0
    assert main(["simples", "configure", "--conditions", "L", "R", "A",
                 "--repetitions", "3"]) == 0
    from contextlab.manifest import plan
    assert len(plan(read_project(project))) == 9
    saved = (project / "contextlab.json").read_bytes()
    assert main(["simples", "configure", "--mode", "demo", "--conditions", "L",
                 "--repetitions", "0"]) == 2
    assert (project / "contextlab.json").read_bytes() == saved


def test_pilot_uses_codex_and_docker_without_calling_model(project, monkeypatch):
    assert register() == 0
    import contextlab.adapters
    monkeypatch.setattr(contextlab.adapters, "run_agent", lambda *a: pytest.fail("Modelo não deve ser chamado"))
    assert main(["simples", "configure", "--mode", "pilot", "--model", "modelo-teste",
                 "--conditions", "L", "--repetitions", "1"]) == 0
    config = read_project(project)
    assert config["evaluation"]["backend"] == "docker"
    assert config["agents"] == [{"id": "codex", "kind": "codex", "model": "modelo-teste"}]
    assert main(["simples", "plan"]) == 0
    assert main(["simples", "context", "--condition", "A"]) == 0


def test_run_requires_explicit_local_authorization(project):
    assert register() == 0
    assert main(["simples", "run"]) == 2
    assert not (project / "runs").exists()


def test_setup_prepares_configured_image_without_changing_mode_or_running_tests(project, monkeypatch, capsys):
    assert register() == 0
    saved = (project / "contextlab.json").read_bytes()
    calls = []
    monkeypatch.setattr("contextlab.environment.setup_image", lambda folder, config, console, recipe:
                        calls.append((folder, config["evaluation"]["image"], recipe)))
    import contextlab.runner
    monkeypatch.setattr(contextlab.runner, "execute", lambda *a, **k: pytest.fail("setup não executa tentativas"))
    assert main(["simples", "setup"]) == 0
    assert calls == [(project, "contextlab-evaluator:local", None)]
    assert (project / "contextlab.json").read_bytes() == saved
    assert not (project / "runs").exists()
    assert "continua em demo local" in capsys.readouterr().out


def test_run_listing_review_and_resume_preserve_submission(project, capsys):
    assert register() == 0
    assert main(["simples", "run", "--trusted-local"]) == 0
    rows = attempts(project)
    assert len(rows) == 1
    assert rows[0]["approval"] == "pending_review"
    assert rows[0]["collected"] == 1
    path = find_attempt(project, rows[0]["attempt_id"])
    submitted = (path / "test_generated.py").read_bytes()
    before = {p: p.read_bytes() for p in (project / "runs").rglob("*") if p.is_file()}
    assert main(["simples", "runs"]) == 0
    assert rows[0]["attempt_id"] in capsys.readouterr().out
    assert main(["simples", "show", rows[0]["attempt_id"]]) == 0
    shown = capsys.readouterr().out
    assert "1 passou" in shown
    assert "test_soma" in shown
    assert "Aguardando revisão" in shown
    assert main(["simples", "show", rows[0]["attempt_id"], "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["approval"] == "pending_review"
    assert main(["simples", "show", rows[0]["attempt_id"], "--code"]) == 0
    assert "Código entregue" in capsys.readouterr().out
    assert before == {p: p.read_bytes() for p in (project / "runs").rglob("*") if p.is_file()}
    assert main(["simples", "review", rows[0]["attempt_id"], "--reviewer", "Teste automatizado",
                 "--behavioral-assertions", "yes", "--no-target-mock", "yes",
                 "--no-production-changes", "yes", "--dependency-doubles", "yes", "--trusted-local"]) == 0
    assert attempts(project)[0]["approval"] == "approved"
    # Dublês das dependências são marcados, sem impedir a aprovação.
    from contextlab.reporting import read_report
    row = read_report(path.parent)["rows"][0]
    assert row["approved"] is True and row["dependency_doubles"] is True
    assert main(["simples", "run", "--resume", rows[0]["batch"], "--trusted-local"]) == 0
    assert len(attempts(project)) == 1
    assert (path / "test_generated.py").read_bytes() == submitted


def test_reference_failure_prevents_generation(project, monkeypatch):
    assert register() == 0
    (project / "tests/test_calculo.py").write_text("from calculo import somar\ndef test_erro():\n    assert somar(2, 3) == 99\n")
    import contextlab.runner
    monkeypatch.setattr(contextlab.runner, "execute", lambda *a, **k: pytest.fail("Não deveria gerar"))
    assert main(["simples", "run", "--trusted-local"]) == 2
    assert not attempts(project)
    assert main(["simples", "runs"]) == 0


def test_unknown_attempt_and_path_escape_are_rejected(project):
    with pytest.raises(ManifestError):
        find_attempt(project, "../01")
    with pytest.raises(ManifestError):
        find_attempt(project, "ausente/01")


def test_attempt_rejects_symlinked_results(project, tmp_path):
    batch = project / "runs/lote"
    batch.mkdir(parents=True)
    (batch / "results").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ManifestError, match="simbólico"):
        find_attempt(project, "lote/01")

from io import StringIO
from pathlib import Path
import subprocess

import pytest
from rich.console import Console

from contextlab.environment import BASE_IMAGE, setup_image
from contextlab.manifest import ManifestError


@pytest.fixture
def docker(monkeypatch):
    class Docker:
        present = False
        running = True
        build_ok = True
        identifier = "sha256:" + "a" * 64

        def __init__(self):
            self.calls = []

        def run(self, command, **kwargs):
            self.calls.append(command)
            if command[1] == "version":
                return subprocess.CompletedProcess(command, 0 if self.running else 1,
                                                   "28.4.0" if self.running else "", "serviço parado")
            if command[1:3] == ["image", "inspect"]:
                return subprocess.CompletedProcess(command, 0 if self.present else 1,
                                                   self.identifier if self.present else "", "No such image")
            if command[1] == "build":
                self.present = self.build_ok
                return subprocess.CompletedProcess(command, 0 if self.build_ok else 1)
            pytest.fail(f"Operação Docker inesperada: {command}")

    fake = Docker()
    monkeypatch.setattr("contextlab.environment.shutil.which", lambda name: "/docker")
    monkeypatch.setattr("contextlab.environment.subprocess.run", fake.run)
    return fake


def prepare(folder, image=BASE_IMAGE, dockerfile=None):
    return setup_image(folder, {"evaluation": {"image": image}}, Console(file=StringIO()), dockerfile)


def test_setup_builds_missing_base_image_without_starting_containers(tmp_path, docker):
    result = prepare(tmp_path)
    assert result == {"image": BASE_IMAGE, "image_id": docker.identifier, "created": True}
    build = next(call for call in docker.calls if call[1] == "build")
    recipe = Path(build[build.index("--file") + 1])
    assert recipe.is_file()
    assert (Path(build[-1]) / ".dockerignore").read_text().splitlines()[-2:] == ["*", "!Dockerfile.evaluator"]
    assert not list(tmp_path.iterdir())


def test_setup_reuses_existing_image_without_replacing_frozen_environment(tmp_path, docker):
    docker.present = True
    result = prepare(tmp_path, image="meu-avaliador:v1")
    assert result["created"] is False
    assert result["image_id"] == docker.identifier
    assert not any(call[1] == "build" for call in docker.calls)


def test_setup_stops_when_service_is_unavailable(tmp_path, docker):
    docker.running = False
    with pytest.raises(ManifestError, match="Docker indisponível"):
        prepare(tmp_path)
    assert len(docker.calls) == 1


def test_setup_explains_missing_executable(tmp_path, docker, monkeypatch):
    monkeypatch.setattr("contextlab.environment.shutil.which", lambda name: None)
    with pytest.raises(ManifestError, match="Docker não encontrado"):
        prepare(tmp_path)
    assert not docker.calls


def test_setup_does_not_build_custom_image_with_base_dependencies(tmp_path, docker):
    with pytest.raises(ManifestError, match="--dockerfile"):
        prepare(tmp_path, image="meu-avaliador:v1")
    assert not any(call[1] == "build" for call in docker.calls)


def test_setup_uses_explicit_project_recipe_and_context(tmp_path, docker):
    recipe = tmp_path / "Dockerfile.evaluator"
    recipe.write_text("FROM python:3.12.11-slim\n")
    prepare(tmp_path, image="meu-avaliador:v1", dockerfile=recipe.name)
    build = next(call for call in docker.calls if call[1] == "build")
    assert build == ["/docker", "build", "--file", str(recipe), "--tag", "meu-avaliador:v1", str(tmp_path)]


def test_setup_reports_build_failure_without_claiming_readiness(tmp_path, docker):
    docker.build_ok = False
    with pytest.raises(ManifestError, match="construção da imagem falhou"):
        prepare(tmp_path)
    assert docker.present is False


@pytest.mark.parametrize("path", ["../Dockerfile", "/tmp/Dockerfile", "ausente"])
def test_setup_rejects_invalid_recipe_before_build(tmp_path, docker, path):
    with pytest.raises(ManifestError):
        prepare(tmp_path, dockerfile=path)
    assert not any(call[1] == "build" for call in docker.calls)


def test_setup_does_not_rebuild_missing_digest(tmp_path, docker):
    with pytest.raises(ManifestError, match="digest"):
        prepare(tmp_path, image="avaliador@sha256:" + "a" * 64)
    assert not any(call[1] == "build" for call in docker.calls)

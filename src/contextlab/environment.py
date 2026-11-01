"""Preparação explícita da imagem do avaliador, antes de congelar uma execução."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .manifest import ManifestError, safe_file


BASE_IMAGE = "contextlab-evaluator:local"


def _query(command: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ManifestError("Não foi possível consultar o Docker; confira se o serviço está disponível.") from exc


def _image_id(docker: str, name: str) -> str | None:
    result = _query([docker, "image", "inspect", "--format", "{{.Id}}", name])
    if result.returncode:
        if "no such image" in result.stderr.lower():
            return None
        raise ManifestError("Falha ao consultar a imagem Docker: " + result.stderr.strip())
    identifier = result.stdout.strip()
    if not identifier.startswith("sha256:"):
        raise ManifestError("O Docker não informou uma identificação válida da imagem.")
    return identifier


def setup_image(folder: Path, config: dict, console, dockerfile: str | None = None) -> dict:
    """Reuse an existing image, or build the configured tag without touching runs."""
    name = config["evaluation"].get("image")
    if not isinstance(name, str) or not name or name.startswith("-") or any(c.isspace() for c in name):
        raise ManifestError("Defina uma imagem válida com configure --image NOME:VERSAO.")
    docker = shutil.which("docker")
    if not docker:
        raise ManifestError("Docker não encontrado. Instale/inicie o Docker antes de usar setup.")
    service = _query([docker, "version", "--format", "{{.Server.Version}}"])
    if service.returncode or not service.stdout.strip():
        raise ManifestError("Docker indisponível. Inicie o serviço Docker e repita setup.\n" + service.stderr.strip())
    identifier = _image_id(docker, name)
    if identifier:
        console.print(f"Imagem disponível: {name}. Reutilizando sem reconstruir.", markup=False)
        return {"image": name, "image_id": identifier, "created": False}

    if "@" in name or name.startswith("sha256:"):
        raise ManifestError("A imagem identificada por digest não está disponível. Restaure essa imagem; setup constrói apenas tags novas.")
    if dockerfile:
        recipe = safe_file(folder, dockerfile)
        context = folder
    elif name == BASE_IMAGE:
        context = Path(__file__).resolve().parents[2]
        recipe = context / "Dockerfile.evaluator"
        if not recipe.is_file():
            raise ManifestError("Dockerfile base ausente. Use a instalação deste repositório ou --dockerfile relativo ao projeto.")
    else:
        raise ManifestError("Imagem personalizada ausente. Informe --dockerfile CAMINHO relativo ao projeto para construí-la.")

    console.print(f"Construindo {name} com {recipe}…", markup=False)
    console.print("A preparação pode baixar dependências. Nenhum agente será chamado.")
    try:
        result = subprocess.run([docker, "build", "--file", str(recipe), "--tag", name, str(context)], timeout=600)
    except subprocess.TimeoutExpired as exc:
        raise ManifestError("A construção excedeu 10 minutos. Confira a saída do Docker e tente setup novamente.") from exc
    except OSError as exc:
        raise ManifestError("Não foi possível iniciar a construção da imagem Docker.") from exc
    if result.returncode:
        raise ManifestError("A construção da imagem falhou. Confira a saída do Docker acima; nenhuma tentativa foi iniciada.")
    identifier = _image_id(docker, name)
    if not identifier:
        raise ManifestError("A construção terminou, mas a imagem configurada não foi encontrada.")
    console.print(f"Imagem preparada: {name}.", markup=False)
    return {"image": name, "image_id": identifier, "created": True}

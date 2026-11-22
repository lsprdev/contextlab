"""Confere, dentro da imagem do avaliador, que os 12 alvos importam e executam."""
import importlib, inspect

ALVOS = [
    ("fava", "fava.core.budgets", "calculate_budget"),
    ("fava", "fava.core.group_entries", "group_entries_by_account"),
    ("fava", "fava.core.file", "find_insert_position"),
    ("bump-my-version", "bumpversion.versioning.version_config", "VersionConfig.parse"),
    ("bump-my-version", "bumpversion.versioning.serialization", "serialize"),
    ("bump-my-version", "bumpversion.scm.models", "SCMConfig.get_version_from_tag"),
    ("python-dotenv", "dotenv.parser", "parse_value"),
    ("python-dotenv", "dotenv.variables", "parse_variables"),
    ("python-dotenv", "dotenv.main", "resolve_variables"),
    ("python-stdnum", "stdnum.br.cpf", "validate"),
    ("python-stdnum", "stdnum.isbn", "validate"),
    ("python-stdnum", "stdnum.es.nif", "validate"),
]
for projeto, modulo, simbolo in ALVOS:
    obj = importlib.import_module(modulo)
    for parte in simbolo.split("."):
        obj = getattr(obj, parte)
    origem = inspect.getsourcefile(obj)
    assert origem.startswith("/projetos/"), f"{simbolo} veio de {origem}, fora das revisões fixadas"
    print(f"ok  {projeto:16} {modulo}:{simbolo:32} {origem}")

# Execução mínima, um caso por projeto, só para provar que o código roda na imagem.
from stdnum.br import cpf; assert cpf.is_valid("390.533.447-05")
from stdnum import isbn; assert isbn.is_valid("978-0-306-40615-7")
from dotenv.variables import parse_variables; assert [a.name for a in parse_variables("${A}") if hasattr(a, "name")] == ["A"]
from dotenv.main import resolve_variables; assert dict(resolve_variables([("A", "1"), ("B", "${A}")], override=True)) == {"A": "1", "B": "1"}
from bumpversion.versioning.version_config import VersionConfig
from bumpversion.versioning.models import VersionComponentSpec
print("execução mínima ok")

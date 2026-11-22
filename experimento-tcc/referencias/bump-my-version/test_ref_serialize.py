"""Referência BMV-02: bumpversion.versioning.serialization.serialize.

Regras: formatos que exigem partes ausentes do contexto são descartados; entre
os restantes, vence o que contém todas as partes obrigatórias, depois o de
menos partes, depois o que aparece antes. Partes iguais ao valor opcional
(0 nas numéricas) não são obrigatórias.
"""
import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.models import VersionComponentSpec, VersionSpec
from bumpversion.versioning.serialization import serialize

FORMATOS = ["{major}.{minor}.{patch}", "{major}.{minor}"]


def _versao(major, minor, patch):
    spec = VersionSpec({nome: VersionComponentSpec() for nome in ("major", "minor", "patch")})
    return spec.create_version({"major": major, "minor": minor, "patch": patch})


def test_patch_zero_usa_o_formato_mais_curto():
    assert serialize(_versao("1", "2", "0"), FORMATOS, {}) == "1.2"


def test_patch_diferente_de_zero_exige_o_formato_completo():
    assert serialize(_versao("1", "2", "3"), FORMATOS, {}) == "1.2.3"


def test_empate_em_tamanho_fica_com_o_primeiro_da_lista():
    formatos = ["{major}.{minor}.{patch}", "{major}-{minor}-{patch}"]
    assert serialize(_versao("1", "2", "3"), formatos, {}) == "1.2.3"


def test_formato_com_parte_ausente_do_contexto_e_descartado():
    formatos = ["{major}.{minor}.{patch}-{build}", "{major}.{minor}.{patch}"]
    assert serialize(_versao("1", "2", "3"), formatos, {}) == "1.2.3"


def test_valores_do_contexto_podem_ser_usados_no_formato():
    formatos = ["{major}.{minor}.{patch}-{build}"]
    assert serialize(_versao("1", "2", "3"), formatos, {"build": "b7"}) == "1.2.3-b7"


def test_sem_formato_utilizavel_lanca_formatting_error():
    with pytest.raises(FormattingError):
        serialize(_versao("1", "2", "3"), ["{major}.{minor}.{patch}-{build}"], {})


def test_contexto_do_chamador_nao_e_alterado():
    contexto = {"build": "b7"}
    serialize(_versao("1", "2", "3"), ["{major}.{minor}.{patch}-{build}"], contexto)
    assert contexto == {"build": "b7"}

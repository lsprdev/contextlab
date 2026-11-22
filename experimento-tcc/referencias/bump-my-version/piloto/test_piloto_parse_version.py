"""Referência do piloto (fora da amostra): bumpversion.versioning.serialization.parse_version."""
import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.serialization import parse_version

PADRAO = r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(-(?P<release>[a-z]+))?"


def test_versao_completa():
    assert parse_version("1.2.3-rc", PADRAO) == {"major": "1", "minor": "2", "patch": "3", "release": "rc"}


def test_grupo_opcional_ausente_vira_texto_vazio():
    assert parse_version("1.2.3", PADRAO)["release"] == ""


@pytest.mark.parametrize("versao, padrao", [("", PADRAO), (None, PADRAO), ("1.2.3", ""), ("abc", PADRAO)])
def test_entradas_vazias_ou_sem_correspondencia_retornam_dict_vazio(versao, padrao):
    assert parse_version(versao, padrao) == {}


def test_padrao_invalido_lanca_erro():
    with pytest.raises(BumpVersionError):
        parse_version("1.2.3", r"(?P<major>\d+")

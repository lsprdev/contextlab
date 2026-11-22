"""Referência BMV-01: bumpversion.versioning.version_config.VersionConfig.parse.

Valores esperados escritos a partir do padrão e das partes configuradas, sem
chamar o alvo para produzi-los.
"""
import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.models import VersionComponentSpec
from bumpversion.versioning.version_config import VersionConfig

PADRAO = r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
PADRAO_COM_RELEASE = PADRAO + r"(-(?P<release>[a-z]+))?"


def _config(padrao=PADRAO, partes=None):
    partes = partes or {nome: VersionComponentSpec() for nome in ("major", "minor", "patch")}
    return VersionConfig(padrao, ("{major}.{minor}.{patch}",), search="{current_version}",
                         replace="{new_version}", part_configs=partes)


def _valores(versao):
    return {nome: versao[nome].value for nome in versao}


def test_versao_simples_produz_as_tres_partes():
    versao = _config().parse("1.2.3")
    assert _valores(versao) == {"major": "1", "minor": "2", "patch": "3"}


def test_guarda_a_cadeia_original():
    assert _config().parse("1.2.3").original == "1.2.3"


def test_padrao_e_procurado_em_qualquer_posicao():
    versao = _config().parse("v1.2.3")
    assert _valores(versao) == {"major": "1", "minor": "2", "patch": "3"}
    assert versao.original == "v1.2.3"


def test_grupo_opcional_ausente_recebe_o_valor_opcional():
    partes = {"major": VersionComponentSpec(), "minor": VersionComponentSpec(), "patch": VersionComponentSpec(),
              "release": VersionComponentSpec(values=["dev", "rc", "final"], optional_value="final")}
    config = _config(PADRAO_COM_RELEASE, partes)
    assert config.parse("1.2.3")["release"].value == "final"
    assert config.parse("1.2.3-rc")["release"].value == "rc"


def test_cadeia_que_nao_corresponde_retorna_none():
    assert _config().parse("abc") is None


def test_cadeia_vazia_retorna_none():
    assert _config().parse("") is None


def test_sem_cadeia_retorna_none():
    assert _config().parse(None) is None


def test_cadeia_invalida_com_raise_error_lanca_excecao():
    with pytest.raises(BumpVersionError):
        _config().parse("abc", raise_error=True)


def test_cadeia_valida_com_raise_error_nao_lanca():
    assert _valores(_config().parse("4.5.6", raise_error=True)) == {"major": "4", "minor": "5", "patch": "6"}

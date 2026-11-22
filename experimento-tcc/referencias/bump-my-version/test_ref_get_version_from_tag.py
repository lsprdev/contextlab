"""Referência BMV-03: bumpversion.scm.models.SCMConfig.get_version_from_tag.

Versões esperadas escritas a partir do modelo da etiqueta e do padrão.
"""
from bumpversion.scm.models import SCMConfig

PADRAO = r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"


def _scm(tag_name="v{new_version}", parse_pattern=PADRAO):
    return SCMConfig(tag=True, push_tag=False, sign_tags=False, tag_name=tag_name, allow_dirty=False,
                     commit=False, message="Bump", parse_pattern=parse_pattern)


def test_etiqueta_com_prefixo_v_retorna_a_versao():
    assert _scm().get_version_from_tag("v1.2.3") == "1.2.3"


def test_etiqueta_sem_versao_retorna_none():
    assert _scm().get_version_from_tag("release-final") is None


def test_prefixo_e_tratado_como_texto_literal():
    scm = _scm("release.{new_version}")
    assert scm.get_version_from_tag("release.1.2.3") == "1.2.3"
    # O ponto do prefixo não funciona como curinga.
    assert scm.get_version_from_tag("releaseX1.2.3") is None


def test_modelo_com_sufixo_usa_so_o_prefixo():
    assert _scm("v{new_version}-final").get_version_from_tag("v1.2.3-final") == "1.2.3"


def test_marcacao_verbose_no_inicio_do_padrao_continua_valendo():
    padrao = r"(?x) (?P<major>\d+) \. (?P<minor>\d+) \. (?P<patch>\d+)"
    assert _scm(parse_pattern=padrao).get_version_from_tag("v1.2.3") == "1.2.3"


def test_barras_invertidas_duplicadas_sao_reduzidas():
    padrao = r"(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)"
    assert _scm(parse_pattern=padrao).get_version_from_tag("v4.5.6") == "4.5.6"

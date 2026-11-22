"""Referência DOT-01: dotenv.parser.parse_value.

O leitor é posicionado no início do valor. Expectativas escritas a partir da
sintaxe documentada do .env: escapes decodificados entre aspas duplas,
preservados entre aspas simples (exceto \\\\ e \\'), comentário só após espaço
em valores sem aspas.
"""
import io

import pytest

from dotenv.parser import Error, Reader, parse_value


def _leitor(texto):
    return Reader(io.StringIO(texto))


def test_valor_sem_aspas():
    leitor = _leitor("abc")
    assert parse_value(leitor) == "abc"
    assert leitor.position.chars == 3


def test_valor_sem_aspas_remove_comentario_apos_espaco_e_para_no_fim_da_linha():
    leitor = _leitor("abc # comentario\nOUTRA=1")
    assert parse_value(leitor) == "abc"
    assert leitor.position.chars == len("abc # comentario")
    assert leitor.position.line == 1


def test_cerquilha_sem_espaco_faz_parte_do_valor():
    assert parse_value(_leitor("abc#def")) == "abc#def"


def test_valor_vazio_no_fim_do_texto():
    leitor = _leitor("")
    assert parse_value(leitor) == ""
    assert leitor.position.chars == 0


def test_valor_vazio_antes_da_quebra_de_linha():
    leitor = _leitor("\nOUTRA=1")
    assert parse_value(leitor) == ""
    assert leitor.position.chars == 0


def test_aspas_simples_preservam_o_conteudo():
    leitor = _leitor("'a b # c' depois")
    assert parse_value(leitor) == "a b # c"
    assert leitor.position.chars == len("'a b # c'")


def test_aspas_duplas_decodificam_quebra_de_linha():
    leitor = _leitor('"linha1\\nlinha2"')
    assert parse_value(leitor) == "linha1\nlinha2"
    assert leitor.position.chars == len('"linha1\\nlinha2"')


def test_aspas_duplas_decodificam_aspas_escapadas():
    assert parse_value(_leitor('"diz \\"oi\\""')) == 'diz "oi"'


def test_aspas_simples_nao_decodificam_quebra_de_linha():
    assert parse_value(_leitor("'linha1\\nlinha2'")) == "linha1\\nlinha2"


def test_aspas_simples_decodificam_aspa_simples_escapada():
    assert parse_value(_leitor("'it\\'s'")) == "it's"


def test_aspas_duplas_podem_conter_quebra_de_linha_real():
    leitor = _leitor('"a\nb"')
    assert parse_value(leitor) == "a\nb"
    assert leitor.position.line == 2


def test_aspas_nao_encerradas_lancam_erro():
    with pytest.raises(Error):
        parse_value(_leitor('"abc'))


def test_codigo_avaliado_vem_do_projeto_e_nao_do_pacote_instalado():
    # A imagem do avaliador tem python-dotenv instalado como dependência de outro
    # projeto; a referência precisa exercitar o código da revisão fixada.
    import dotenv.parser
    assert "site-packages" not in dotenv.parser.__file__

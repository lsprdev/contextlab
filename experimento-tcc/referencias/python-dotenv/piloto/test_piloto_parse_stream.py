"""Referência do piloto (fora da amostra): dotenv.parser.parse_stream."""
import io

from dotenv.parser import parse_stream


def _pares(texto):
    return [(b.key, b.value, b.error) for b in parse_stream(io.StringIO(texto))]


def test_pares_simples_e_comentarios():
    assert _pares("A=1\n# comentario\nB='dois'\n") == [("A", "1", False), (None, None, False), ("B", "dois", False)]


def test_chave_sem_valor():
    assert _pares("SOZINHA\n") == [("SOZINHA", None, False)]


def test_export_e_aceito():
    assert _pares("export A=1\n") == [("A", "1", False)]


def test_linha_invalida_gera_erro_e_continua():
    assert _pares("A='aberta\nB=2\n")[-1] == ("B", "2", False)
    assert any(erro for _, _, erro in _pares("A='aberta\nB=2\n"))


def test_texto_vazio():
    assert _pares("") == []

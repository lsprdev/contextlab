from contextlib import closing
import sqlite3

import pytest

from orcamentos.orcamentos import calcular_orcamento
from orcamentos.repositorio import inicializar_banco, salvar_orcamento
from orcamentos.schemas import Pedido


def test_rollback_remove_orcamento_e_itens_quando_insercao_falha(tmp_path):
    path = tmp_path / "teste.sqlite3"
    inicializar_banco(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TRIGGER falha BEFORE INSERT ON itens WHEN NEW.descricao = 'rejeitar' "
                           "BEGIN SELECT RAISE(ABORT, 'falha controlada'); END")
    pedido = Pedido(itens=[{"descricao": name, "preco_unitario": "1.00", "quantidade": 1}
                           for name in ("aceitar", "rejeitar")])
    with pytest.raises(sqlite3.IntegrityError, match="falha controlada"):
        salvar_orcamento(path, pedido, calcular_orcamento(pedido))
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT count(*) FROM orcamentos").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM itens").fetchone() == (0,)

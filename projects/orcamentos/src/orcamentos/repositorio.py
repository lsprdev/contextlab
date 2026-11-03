"""Persistência SQLite real. Cada operação abre e fecha sua própria conexão."""
from contextlib import closing
from decimal import Decimal, localcontext
from pathlib import Path
import sqlite3

from orcamentos.schemas import ItemPedido, OrcamentoSalvo, Pedido, ResumoOrcamento


def _conectar(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def inicializar_banco(path: str | Path) -> None:
    """Cria as tabelas se ausentes, preservando os registros existentes."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(_conectar(path)) as connection, connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS orcamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cupom TEXT,
                entrega TEXT NOT NULL CHECK (entrega IN ('padrao', 'expressa')),
                subtotal_centavos INTEGER NOT NULL,
                desconto_centavos INTEGER NOT NULL,
                frete_centavos INTEGER NOT NULL,
                total_centavos INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
                descricao TEXT NOT NULL,
                preco_centavos INTEGER NOT NULL,
                quantidade INTEGER NOT NULL
            );
        """)


def _centavos(value: Decimal) -> int:
    with localcontext() as context:
        context.prec = 28
        return int(value * 100)


def _reais(value: int) -> Decimal:
    with localcontext() as context:
        context.prec = 28
        return (Decimal(value) / 100).quantize(Decimal("0.01"))


def salvar_orcamento(path: str | Path, pedido: Pedido, resumo: ResumoOrcamento) -> OrcamentoSalvo:
    """Salva orçamento e itens na mesma transação, usando valores em centavos."""
    with closing(_conectar(path)) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO orcamentos (cupom, entrega, subtotal_centavos, desconto_centavos, frete_centavos, total_centavos) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (pedido.cupom, pedido.entrega, *(_centavos(getattr(resumo, key))
             for key in ("subtotal", "desconto", "frete", "total"))),
        )
        identifier = cursor.lastrowid
        connection.executemany(
            "INSERT INTO itens (orcamento_id, descricao, preco_centavos, quantidade) VALUES (?, ?, ?, ?)",
            [(identifier, item.descricao, _centavos(item.preco_unitario), item.quantidade) for item in pedido.itens],
        )
    return OrcamentoSalvo(id=identifier, itens=pedido.itens, cupom=pedido.cupom, entrega=pedido.entrega,
                          **{key: getattr(resumo, key) for key in ("subtotal", "desconto", "frete", "total")})


def buscar_orcamento(path: str | Path, identifier: int) -> OrcamentoSalvo | None:
    """Recupera os valores gravados, sem recalcular preços ou aplicar políticas atuais."""
    with closing(_conectar(path)) as connection:
        row = connection.execute("SELECT * FROM orcamentos WHERE id = ?", (identifier,)).fetchone()
        if row is None:
            return None
        items = connection.execute("SELECT * FROM itens WHERE orcamento_id = ? ORDER BY id", (identifier,)).fetchall()
    return OrcamentoSalvo(
        id=row["id"], cupom=row["cupom"], entrega=row["entrega"],
        itens=[ItemPedido(descricao=item["descricao"], preco_unitario=_reais(item["preco_centavos"]),
                         quantidade=item["quantidade"]) for item in items],
        **{key: _reais(row[key + "_centavos"]) for key in ("subtotal", "desconto", "frete", "total")},
    )

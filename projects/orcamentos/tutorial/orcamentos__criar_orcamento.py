"""Entrega HTTP autoral com SQLite temporário real, sem mocks."""
from fastapi.testclient import TestClient

from orcamentos.api import create_app


def test_cria_e_consulta_orcamento(tmp_path):
    with TestClient(create_app(tmp_path / "teste.sqlite3")) as client:
        response = client.post("/orcamentos", json={
            "itens": [{"descricao": "Livro", "preco_unitario": "100.00", "quantidade": 2}],
            "cupom": "DESC10", "entrega": "padrao",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == "195.00"
        persisted = client.get(f"/orcamentos/{data['id']}")
        assert persisted.status_code == 200
        assert persisted.json() == data

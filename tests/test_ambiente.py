"""A API aceita só os valores padronizados de ambiente e local, e recusa os antigos com 422.

O cliente (fixture em conftest.py) usa um banco SQLite em memória.
"""

import pytest


def criar_obra(cliente, ambiente):
    resposta = cliente.post("/obras/", json={"nome": f"Obra {ambiente}", "ambiente": ambiente})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["id"]


@pytest.mark.parametrize("ambiente", ["Aberto", "Fechado", "Misto"])
def test_cadastra_obra_com_ambiente_padronizado(cliente, ambiente):
    obra_id = criar_obra(cliente, ambiente)
    assert cliente.get(f"/obras/{obra_id}").json()["ambiente"] == ambiente


@pytest.mark.parametrize("ambiente", ["Aberto (Sujeito ao clima)", "Fechado (Coberto)", "Misto (Aberto e Fechado)", "fechado"])
def test_recusa_ambiente_fora_do_padrao(cliente, ambiente):
    assert cliente.post("/obras/", json={"nome": "Obra", "ambiente": ambiente}).status_code == 422


def test_diario_aceita_local_padronizado(cliente):
    obra_id = criar_obra(cliente, "Misto")
    for local in ("Interior", "Exterior"):
        resposta = cliente.post("/diarios/", json={"data": "2026-10-05", "local_dia": local, "obra_id": obra_id})
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["local_dia"] == local


@pytest.mark.parametrize("local", ["Frente da Obra", "Interior (Coberto)", "Exterior (Céu Aberto)"])
def test_diario_recusa_local_fora_do_padrao(cliente, local):
    obra_id = criar_obra(cliente, "Aberto")
    resposta = cliente.post("/diarios/", json={"data": "2026-10-05", "local_dia": local, "obra_id": obra_id})
    assert resposta.status_code == 422


def test_converter_orcamento_usa_ambiente_padronizado(cliente):
    orcamento = cliente.post("/orcamentos/", json={
        "cliente": "Cliente", "nome_projeto": "Projeto", "custo_material": 1000.0,
        "custo_mao_de_obra": 500.0, "lucro": 300.0, "valor_total": 1800.0,
    }).json()
    rota = f"/orcamentos/{orcamento['id']}/converter"
    dados = {"endereco": "Rua A, 1", "data_inicio": "2026-10-05"}

    assert cliente.post(rota, json={**dados, "ambiente": "Misto (Aberto e Fechado)"}).status_code == 422
    assert cliente.post(rota, json={**dados, "ambiente": "Misto"}).status_code == 200
    assert [o["ambiente"] for o in cliente.get("/obras/").json()] == ["Misto"]

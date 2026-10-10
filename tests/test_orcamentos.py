"""Orçamentos: lucro em reais, total calculado pelo servidor e status padronizados."""

import pytest

ORCAMENTO = {"cliente": "Cliente", "nome_projeto": "Projeto",
             "custo_material": 30000.0, "custo_mao_de_obra": 5000.0, "lucro": 10500.0}


def criar(cliente, **mudancas):
    resposta = cliente.post("/orcamentos/", json={**ORCAMENTO, **mudancas})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_total_e_calculado_pelo_servidor(cliente):
    orc = cliente.post("/orcamentos/", json={**ORCAMENTO, "valor_total": 1.0}).json()
    assert orc["valor_total"] == 45500.0
    assert orc["lucro"] == 10500.0
    assert orc["status"] == "Em análise"


@pytest.mark.parametrize("campo", ["custo_material", "custo_mao_de_obra", "lucro"])
def test_recusa_valor_negativo(cliente, campo):
    assert cliente.post("/orcamentos/", json={**ORCAMENTO, campo: -1.0}).status_code == 422


@pytest.mark.parametrize("status", ["Aprovado", "Recusado", "Em análise"])
def test_aceita_status_manuais(cliente, status):
    orc = criar(cliente)
    assert cliente.put(f"/orcamentos/{orc['id']}/status", json={"status": status}).status_code == 200
    assert cliente.get("/orcamentos/").json()[0]["status"] == status


@pytest.mark.parametrize("status", ["Obra Negada", "Convertido em Obra", "aprovado"])
def test_recusa_status_fora_do_padrao_ou_reservado(cliente, status):
    orc = criar(cliente)
    assert cliente.put(f"/orcamentos/{orc['id']}/status", json={"status": status}).status_code == 422


def test_orcamento_convertido_nao_muda_mais_de_status(cliente):
    orc = criar(cliente)
    conversao = {"endereco": "Rua A, 1", "ambiente": "Aberto", "data_inicio": "2026-10-05"}
    assert cliente.post(f"/orcamentos/{orc['id']}/converter", json=conversao).status_code == 200
    assert cliente.put(f"/orcamentos/{orc['id']}/status", json={"status": "Em análise"}).status_code == 400
    assert cliente.post(f"/orcamentos/{orc['id']}/converter", json=conversao).status_code == 400
    assert len(cliente.get("/obras/").json()) == 1

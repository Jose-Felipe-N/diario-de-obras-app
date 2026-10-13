"""Fontes mostradas na tela do Analista IA e registro das avaliações 👍/👎."""

import json

import config
from tela_analista import descrever_fontes


def test_fontes_em_linguagem_do_engenheiro_sem_repeticao():
    uso = {"ferramentas": [
        {"nome": "diarios", "argumentos": {"inicio": "2026-09-28", "fim": "2026-10-04", "obra": "Galpão Logístico"}},
        {"nome": "buscar_observacoes", "argumentos": {"consulta": "fornecedor atrasou"}},
        {"nome": "gastos", "argumentos": {"categoria": "Material de Construção", "obra": "Casa"}},
        {"nome": "observacoes", "argumentos": {}},
        {"nome": "diarios", "argumentos": {"inicio": "2026-09-28", "fim": "2026-10-04", "obra": "Galpão Logístico"}},
    ]}
    assert descrever_fontes(uso) == [
        "Diários de 28/09/2026 a 04/10/2026 (Galpão Logístico)",
        'Busca por tema nas observações: "fornecedor atrasou"',
        "Gastos de Material de Construção (Casa)",
        "Observações dos diários de todo o período",
    ]


def test_sem_ferramentas_sem_fontes():
    assert descrever_fontes({"ferramentas": []}) == [] and descrever_fontes(None) == []


def test_feedback_vai_para_o_arquivo(cliente):
    dados = {"pergunta": "qual obra ta atrasada?", "resposta": "O Galpão.", "nota": "negativo", "obra_id": None,
             "ferramentas": [{"nome": "listar_obras", "argumentos": {}}]}
    assert cliente.post("/ia/feedback", json=dados).status_code == 200
    [linha] = config.FEEDBACK_ARQUIVO.read_text(encoding="utf-8").splitlines()
    registro = json.loads(linha)
    assert registro["nota"] == "negativo" and registro["pergunta"] == "qual obra ta atrasada?" and "quando" in registro


def test_feedback_com_nota_invalida_e_recusado(cliente):
    dados = {"pergunta": "p", "resposta": "r", "nota": "talvez"}
    assert cliente.post("/ia/feedback", json=dados).status_code == 422

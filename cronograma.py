"""Monta o cronograma inicial da tela Nova Obra a partir das etapas escolhidas (sem Streamlit, para poder testar).

O progresso da obra é a soma dos pesos das etapas concluídas, por isso os pesos precisam somar 100%.
"""

import json
from pathlib import Path

CAMINHO_ETAPAS = Path(__file__).parent / "dados" / "etapas_comuns.json"
TOLERANCIA_PESOS = 0.5  # pontos percentuais


def carregar_etapas_comuns(caminho=CAMINHO_ETAPAS):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)["etapas"]


def montar_etapas(escolhidas, referencia):
    """Linhas da tabela para as etapas escolhidas: na ordem natural da obra, numeradas e com os
    pesos de referência redistribuídos para somar exatamente 100 (uma casa decimal)."""
    selecionadas = [e for e in referencia if e["nome"] in set(escolhidas)]
    if not selecionadas:
        return []
    total = sum(e["peso"] for e in selecionadas)
    pesos = [round(e["peso"] / total * 100, 1) for e in selecionadas]
    maior = pesos.index(max(pesos))
    pesos[maior] = round(pesos[maior] + 100 - sum(pesos), 1)  # sobra do arredondamento vai para a maior
    return [{"Nome da Etapa": f"{i}. {e['nome']}", "Peso (%)": peso, "Dias Estimados": e["dias"]}
            for i, (e, peso) in enumerate(zip(selecionadas, pesos), start=1)]


def problema_nos_pesos(etapas):
    """Mensagem se os pesos das etapas não somam 100%, ou None. Sem etapas, não há problema."""
    if not etapas:
        return None
    soma = sum(e["peso_percentual"] for e in etapas)
    if abs(soma - 100) <= TOLERANCIA_PESOS:
        return None
    return (f"Os pesos das etapas somam {_pct(soma)}, e precisam somar 100%: o progresso da obra é a "
            "soma dos pesos das etapas concluídas. Ajuste a coluna Peso (%) e salve de novo.")


def _pct(valor):
    return f"{valor:g}%".replace(".", ",")

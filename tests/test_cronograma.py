"""Cronograma inicial da Nova Obra: só as etapas escolhidas, na ordem da obra, com pesos somando 100%."""

from cronograma import carregar_etapas_comuns, montar_etapas, problema_nos_pesos

REFERENCIA = carregar_etapas_comuns()


def test_lista_de_referencia_tem_nomes_unicos_e_valores_positivos():
    nomes = [e["nome"] for e in REFERENCIA]
    assert len(nomes) == len(set(nomes))
    assert all(e["peso"] > 0 and e["dias"] > 0 for e in REFERENCIA)


def test_contrato_parcial_redistribui_os_pesos():
    linhas = montar_etapas(["Estrutura", "Fundação"], REFERENCIA)
    assert linhas == [
        {"Nome da Etapa": "1. Fundação", "Peso (%)": 50.0, "Dias Estimados": 15},
        {"Nome da Etapa": "2. Estrutura", "Peso (%)": 50.0, "Dias Estimados": 20},
    ]


def test_pesos_somam_exatamente_100_com_arredondamento():
    for escolhidas in (["Fundação", "Alvenaria", "Pintura"], [e["nome"] for e in REFERENCIA], ["Pisos"]):
        linhas = montar_etapas(escolhidas, REFERENCIA)
        assert round(sum(l["Peso (%)"] for l in linhas), 1) == 100.0


def test_sem_escolha_a_tabela_comeca_vazia():
    assert montar_etapas([], REFERENCIA) == []


def test_aviso_quando_os_pesos_nao_somam_100():
    assert problema_nos_pesos([]) is None
    assert problema_nos_pesos([{"peso_percentual": 60}, {"peso_percentual": 40.3}]) is None
    aviso = problema_nos_pesos([{"peso_percentual": 50}, {"peso_percentual": 35}])
    assert "somam 85%" in aviso

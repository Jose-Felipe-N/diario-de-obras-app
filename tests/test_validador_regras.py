"""Casos sintéticos que provam que cada regra do validador pega a violação certa.

Sem estes testes, uma regra que "passa" com dados vazios não provaria nada: ela poderia
estar passando porque não olha o que deveria.
"""

import pytest

from avaliacao import validacao_dados as v


@pytest.fixture(scope="module")
def referencia():
    pasta = v.RAIZ / "dados"
    return v.ler_json(pasta / "eventos.json"), v.ler_json(pasta / "catalogo.json")


def diario(**mudancas):
    """Diário válido da Casa Condomínio (Alvenaria, quarta 09/09, dia seco, jornada cheia)."""
    base = {
        "obra": "Casa Condomínio", "data": "2026-09-09", "etapa": "2. Alvenaria",
        "clima_manha": "Sol", "clima_tarde": "Sol", "local": "Exterior", "evento": None,
        "efetivo": [{"funcao": "Pedreiro", "quantidade": 3, "horas": 8}],
        "equipamentos": [{"nome": "Betoneira", "tipo": "Maquinário Pesado", "quantidade": 1}],
        "gastos": [{"item": "Tijolo", "categoria": "Material de Construção", "valor": 850.0}],
    }
    base.update(mudancas)
    return base


REFORMA = {
    "obra": "Reforma Loja Shopping", "data": "2026-08-12", "etapa": "2. Revestimento e Pintura",
    "local": "Interior", "efetivo": [{"funcao": "Pintor", "quantidade": 2, "horas": 8}],
    "equipamentos": [{"nome": "Andaime", "tipo": "EPI/EPC", "quantidade": 2}],
    "gastos": [{"item": "Tinta", "categoria": "Material de Construção", "valor": 420.0}],
}
GALPAO = {
    "obra": "Galpão Logístico", "data": "2026-09-16", "etapa": "2. Estrutura Metálica",
    "local": "Exterior", "efetivo": [{"funcao": "Soldador", "quantidade": 2, "horas": 8}],
    "equipamentos": [{"nome": "Máquina de solda", "tipo": "Ferramenta Elétrica", "quantidade": 1}],
    "gastos": [{"item": "Eletrodo", "categoria": "Material de Construção", "valor": 180.0}],
}
PARADO = {"efetivo": [], "equipamentos": [], "gastos": []}


def montar(referencia, diarios, textos=None):
    """Monta um Dados com os diários dados; `textos` mapeia o índice do diário ao texto de rotina."""
    eventos, catalogo = referencia
    rotina = [{"obra": diarios[i]["obra"], "data": diarios[i]["data"], "texto": t}
              for i, t in (textos or {}).items()]
    return v.Dados(eventos=eventos, catalogo=catalogo,
                   esqueleto={"obras": [], "orcamentos": [], "diarios": list(diarios)}, rotina=rotina)


REGRAS_POR_DIARIO = [
    v.checar_catalogo, v.checar_compatibilidade, v.checar_clima_e_local, v.checar_jornada,
    v.checar_dia_parado, v.checar_dia_perdido, v.checar_palavras_de_clima, v.checar_rotina,
    v.checar_repeticao, v.checar_palavras_de_evento,
]


def test_diario_valido_passa_em_todas_as_regras_por_diario(referencia):
    dados = montar(referencia, [diario()],
                   {0: "Subimos mais oito fiadas na parede da cozinha, argamassa rendeu bem."})
    for regra in REGRAS_POR_DIARIO:
        assert regra(dados) == [], regra.__name__


VIOLACOES = [
    # (descrição, mudanças no diário, texto de rotina, regra, trecho esperado na violação)
    ("categoria Outros", {"gastos": [{"item": "Tijolo", "categoria": "Outros", "valor": 100.0}]},
     None, v.checar_catalogo, "categoria fora da lista da tela"),
    ("função fora do catálogo", {"efetivo": [{"funcao": "Encanador", "quantidade": 1, "horas": 8}]},
     None, v.checar_catalogo, "função fora do catálogo"),
    ("tipo de equipamento errado", {"equipamentos": [{"nome": "Betoneira", "tipo": "Pesado", "quantidade": 1}]},
     None, v.checar_catalogo, "com tipo 'Pesado'"),
    ("item fora do catálogo", {"gastos": [{"item": "Cimento CSN", "categoria": "Material de Construção", "valor": 90.0}]},
     None, v.checar_catalogo, "item de gasto fora do catálogo"),
    ("soldador na alvenaria", {"efetivo": [{"funcao": "Soldador", "quantidade": 1, "horas": 8}]},
     None, v.checar_compatibilidade, "função Soldador incompatível"),
    ("guindaste na alvenaria", {"equipamentos": [{"nome": "Guindaste", "tipo": "Maquinário Pesado", "quantidade": 1}]},
     None, v.checar_compatibilidade, "equipamento Guindaste incompatível"),
    ("mão de obra externa na casa",
     {"gastos": [{"item": "Empreiteira de solda", "categoria": "Mão de Obra Externa", "valor": 900.0}]},
     None, v.checar_compatibilidade, "item Empreiteira de solda incompatível"),
    ("reforma no exterior", {**REFORMA, "local": "Exterior"},
     None, v.checar_clima_e_local, "local 'Exterior' não permitido"),
    ("clima inválido", {"clima_manha": "Granizo"}, None, v.checar_clima_e_local, "clima inválido"),
    ("tempestade no exterior com jornada cheia", {"clima_tarde": "Tempestade"},
     None, v.checar_jornada, "tempestade no exterior exige dia parado"),
    ("chuva no exterior com jornada cheia", {"clima_manha": "Chuva"},
     None, v.checar_jornada, "chuva no exterior exige jornada"),
    ("jornada reduzida sem motivo na reforma",
     {**REFORMA, "efetivo": [{"funcao": "Pintor", "quantidade": 2, "horas": 4}]},
     None, v.checar_jornada, "sem clima ruim no exterior nem evento"),
    ("dia parado com marmitex", {**PARADO, "gastos": [{"item": "Marmitex", "categoria": "Alimentação", "valor": 60.0}]},
     None, v.checar_dia_parado, "gasto de Alimentação"),
    ("dia parado com equipamento",
     {**PARADO, "equipamentos": [{"nome": "Betoneira", "tipo": "Maquinário Pesado", "quantidade": 1}]},
     None, v.checar_dia_parado, "equipamento operando"),
    ("dia perdido com jornada cheia", {},
     "Dia perdido, a parede dos fundos não avançou quase nada hoje.", v.checar_dia_perdido, "fala em dia perdido"),
    ("chuva citada em dia de sol", {},
     "Chuva fina atrapalhou o reboco externo, mas a parede subiu.", v.checar_palavras_de_clima, "cita chuva"),
    ("chuva à tarde com chuva só de manhã",
     {"clima_manha": "Chuva", "clima_tarde": "Sol", "efetivo": [{"funcao": "Pedreiro", "quantidade": 3, "horas": 5}]},
     "Choveu à tarde e o pessoal recolheu as ferramentas mais cedo.", v.checar_palavras_de_clima, "cita chuva"),
    ("obra fechada citando clima", REFORMA,
     "Chuva forte lá fora, pintura do salão seguiu normal hoje.", v.checar_palavras_de_clima, "obra fechada"),
    ("sol citado em dia nublado", {"clima_manha": "Nublado", "clima_tarde": "Nublado"},
     "Sol forte o dia todo, assentamento rendeu bem na parede norte.", v.checar_palavras_de_clima, "cita sol"),
    ("palavra-chave de evento na rotina", {},
     "Concessionária passou para medir o ramal e o assentamento seguiu.", v.checar_palavras_de_evento,
     "palavra-chave do E01"),
    ("tema de evento na rotina", {},
     "Fornecedor entregou a areia no horário e o assentamento seguiu.", v.checar_palavras_de_evento,
     "tema de evento"),
    ("rotina num dia de evento",
     {"data": "2026-08-27", "etapa": "1. Fundação", "evento": "E01"},
     "Escavação das valas seguiu firme, armação começou à tarde.", v.checar_rotina, "rotina num dia de evento"),
]


@pytest.mark.parametrize("descricao, mudancas, texto, regra, trecho", VIOLACOES, ids=[c[0] for c in VIOLACOES])
def test_regra_acusa_violacao(referencia, descricao, mudancas, texto, regra, trecho):
    dados = montar(referencia, [diario(**mudancas)], {0: texto} if texto else None)
    violacoes = regra(dados)
    assert any(trecho in x for x in violacoes), f"{descricao}: esperava '{trecho}' em {violacoes}"


CASOS_VALIDOS = [
    # (descrição, mudanças no diário, texto de rotina, regras que não podem acusar nada)
    ("chuva no interior do galpão com jornada cheia", {**GALPAO, "local": "Interior", "clima_tarde": "Chuva"},
     None, [v.checar_jornada, v.checar_clima_e_local]),
    ("chuva no exterior com 5 h",
     {"clima_manha": "Chuva", "efetivo": [{"funcao": "Pedreiro", "quantidade": 3, "horas": 5}]},
     None, [v.checar_jornada]),
    ("tempestade no exterior com dia parado", {**PARADO, "clima_manha": "Tempestade"},
     None, [v.checar_jornada, v.checar_dia_parado]),
    ("dia parado só com locação", {**PARADO, "clima_manha": "Tempestade",
                                   "gastos": [{"item": "Aluguel de andaime", "categoria": "Locação", "valor": 150.0}]},
     None, [v.checar_dia_parado, v.checar_compatibilidade]),
    ("evento explica jornada reduzida na reforma",
     {**REFORMA, "data": "2026-07-16", "etapa": "1. Demolição", "evento": "E16",
      "efetivo": [{"funcao": "Servente", "quantidade": 3, "horas": 4}],
      "equipamentos": [{"nome": "Caminhão", "tipo": "Veículo", "quantidade": 1}],
      "gastos": [{"item": "Aluguel de caçamba", "categoria": "Locação", "valor": 380.0}]},
     None, [v.checar_jornada, v.checar_compatibilidade, v.checar_palavras_de_clima]),
    ("'solda' não conta como 'sol'", {**GALPAO, "clima_manha": "Nublado", "clima_tarde": "Nublado"},
     "Solda das tesouras do vão 3 concluída, montagem segue pela cobertura.", [v.checar_palavras_de_clima]),
    ("chuva citada no período certo",
     {"clima_tarde": "Chuva", "efetivo": [{"funcao": "Pedreiro", "quantidade": 3, "horas": 5}]},
     "Garoa à tarde, recolhemos o material e a parede ficou coberta.", [v.checar_palavras_de_clima, v.checar_jornada]),
]


@pytest.mark.parametrize("descricao, mudancas, texto, regras", CASOS_VALIDOS, ids=[c[0] for c in CASOS_VALIDOS])
def test_caso_valido_nao_e_acusado(referencia, descricao, mudancas, texto, regras):
    dados = montar(referencia, [diario(**mudancas)], {0: texto} if texto else None)
    for regra in regras:
        assert regra(dados) == [], f"{descricao}: {regra.__name__} acusou {regra(dados)}"


def test_repeticao_aceita_duas_e_recusa_tres(referencia):
    texto = "Assentamento da parede norte avançou bem, sem novidade no canteiro."
    datas = ["2026-09-09", "2026-09-10", "2026-09-11"]
    diarios = [diario(data=d) for d in datas]
    assert v.checar_repeticao(montar(referencia, diarios[:2], {0: texto, 1: texto})) == []
    violacoes = v.checar_repeticao(montar(referencia, diarios, {0: texto, 1: texto, 2: texto}))
    assert any("repetido 3 vezes" in x for x in violacoes)


def test_forma_recusa_rotina_longa_demais(referencia):
    texto = ("Assentamento da parede norte avançou bem durante todo o dia, com a turma completa, "
             "argamassa rendendo e a betoneira funcionando sem nenhuma parada até o fim do expediente.")
    violacoes = v.checar_forma(montar(referencia, [diario()], {0: texto}))
    assert any("fora de 55–110" in x for x in violacoes)


def test_restricoes_acusam_diario_num_furo(referencia):
    violacoes = v.checar_restricoes(montar(referencia, [diario(data="2026-10-07")]))
    assert any("Casa Condomínio 2026-10-07: deveria estar sem diário" in x for x in violacoes)


def test_restricoes_acusam_segunda_chuva_na_semana_passada(referencia):
    chuva = diario(**{**GALPAO, "data": "2026-10-01", "clima_tarde": "Chuva"})
    violacoes = v.checar_restricoes(montar(referencia, [chuva]))
    assert any("esperado só 2026-10-02" in x for x in violacoes)


def test_eventos_acusam_evento_nao_plantado(referencia):
    violacoes = v.checar_eventos_plantados(montar(referencia, [diario()]))
    assert any(x.startswith("E01 (Casa Condomínio 2026-08-27): não plantado") for x in violacoes)


def test_calendario_acusa_dia_util_sem_diario(referencia):
    violacoes = v.checar_calendario(montar(referencia, [diario()]))
    assert any("dia útil sem diário: Casa Condomínio 2026-09-10" in x for x in violacoes)

"""Gera os dados congelados de avaliação: dados/esqueleto.json.

Executado uma vez; o resultado é versionado e o seed só o carrega. É determinístico:
com a mesma SEMENTE e os mesmos eventos.json e catalogo.json, o arquivo sai idêntico.

Lê de dados/eventos.json as obras, as etapas, as restrições do calendário e os
eventos plantados, e de dados/catalogo.json as funções, os equipamentos e os itens
de gasto compatíveis com cada etapa. As regras de clima, local e jornada são as do
validador (avaliacao/validacao_dados.py), rodado no final.

As observações de rotina não são geradas aqui: ficam em dados/observacoes_rotina.json.

Uso (a partir da raiz do projeto):

    python scripts/gerar_esqueleto.py                 # não sobrescreve um esqueleto diferente
    python scripts/gerar_esqueleto.py --sobrescrever
"""

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from avaliacao import validacao_dados as v  # noqa: E402

SEMENTE = 20261008
PASTA = RAIZ / "dados"
SAIDA = PASTA / "esqueleto.json"

ENDERECOS = {
    "Casa Condomínio": "Rua das Flores, 123",
    "Reforma Loja Shopping": "Av. Comercial, 400",
    "Galpão Logístico": "Rodovia BR, Km 12",
}

# Peso (%) e dias estimados de cada etapa, como no seed original. As datas vêm do eventos.json.
ETAPAS_PLANEJADAS = {
    "Casa Condomínio": [("1. Fundação", 20, 15), ("2. Alvenaria", 30, 30), ("3. Telhado", 15, 10),
                        ("4. Acabamento", 35, 40)],
    "Reforma Loja Shopping": [("1. Demolição", 30, 10), ("2. Revestimento e Pintura", 70, 40)],
    "Galpão Logístico": [("1. Terraplanagem", 15, 15), ("2. Estrutura Metálica", 45, 40),
                         ("3. Piso Industrial", 40, 20)],
}

CLIMA = (["Sol", "Nublado", "Chuva", "Tempestade"], [55, 25, 15, 5])
TARDE_REPETE_MANHA = 0.6
FRACAO_DOMINGOS = 0.2
CHUVA_HORAS = [4, 5, 6]
PROB_PARADO_SEM_EFETIVO = 0.5
# Estrutura Metálica: chance de trabalhar na área coberta (refúgio na chuva, pré-montagem no seco).
PROB_INTERIOR_NA_CHUVA = 0.6
PROB_INTERIOR_NO_SECO = 0.2

# Equipe por etapa: (função, mínimo, máximo) sempre presentes e (função, mínimo, máximo, chance) eventuais.
EQUIPES = {
    "1. Fundação": ([("Pedreiro", 2, 3), ("Servente", 2, 4)],
                    [("Armador", 1, 2, 0.6), ("Carpinteiro", 1, 2, 0.5), ("Mestre de Obras", 1, 1, 0.7)]),
    "2. Alvenaria": ([("Pedreiro", 3, 4), ("Servente", 2, 4)], [("Mestre de Obras", 1, 1, 0.7)]),
    "1. Demolição": ([("Servente", 3, 5), ("Pedreiro", 1, 2)], [("Mestre de Obras", 1, 1, 0.6)]),
    "2. Revestimento e Pintura": ([("Pintor", 2, 3), ("Pedreiro", 1, 3)],
                                  [("Servente", 1, 2, 0.7), ("Eletricista", 1, 1, 0.4)]),
    "1. Terraplanagem": ([("Operador de Máquinas", 1, 2), ("Servente", 2, 3)], [("Mestre de Obras", 1, 1, 0.6)]),
    "Intervalo": ([("Servente", 2, 2), ("Mestre de Obras", 1, 1)], []),
    "2. Estrutura Metálica": ([("Soldador", 2, 3), ("Montador", 2, 4), ("Servente", 2, 3)],
                              [("Eletricista", 1, 1, 0.3), ("Mestre de Obras", 1, 1, 0.6)]),
}

# Equipamentos por etapa: (nome, chance no dia, quantidade mínima, máxima). Guindaste só no exterior.
EQUIPAMENTOS = {
    "1. Fundação": [("Retroescavadeira", 0.5, 1, 1), ("Betoneira", 0.6, 1, 1), ("Compactador", 0.3, 1, 1),
                    ("Caminhão", 0.3, 1, 1)],
    "2. Alvenaria": [("Betoneira", 0.8, 1, 1), ("Andaime", 0.5, 2, 6)],
    "1. Demolição": [("Caminhão", 0.6, 1, 1), ("Gerador", 0.3, 1, 1)],
    "2. Revestimento e Pintura": [("Andaime", 0.7, 2, 4)],
    "1. Terraplanagem": [("Retroescavadeira", 0.9, 1, 2), ("Compactador", 0.6, 1, 1), ("Caminhão", 0.7, 1, 2)],
    "Intervalo": [("Caminhão", 0.5, 1, 1)],
    "2. Estrutura Metálica": [("Guindaste", 0.8, 1, 1), ("Máquina de solda", 0.8, 1, 2), ("Gerador", 0.3, 1, 1)],
}
SO_NO_EXTERIOR = {"Guindaste"}

# Gastos por etapa: (item, chance no dia).
GASTOS = {
    "1. Fundação": [("Cimento", 0.5), ("Areia", 0.3), ("Brita", 0.3), ("Vergalhão", 0.4), ("Madeira", 0.2),
                    ("Diesel", 0.3), ("Marmitex", 0.2)],
    "2. Alvenaria": [("Tijolo", 0.5), ("Cimento", 0.5), ("Areia", 0.3), ("Aluguel de andaime", 0.15),
                     ("Marmitex", 0.2)],
    "1. Demolição": [("Aluguel de caçamba", 0.6), ("Marmitex", 0.2)],
    "2. Revestimento e Pintura": [("Tinta", 0.4), ("Massa corrida", 0.3), ("Cimento", 0.2), ("Areia", 0.15),
                                  ("Aluguel de andaime", 0.15), ("Gesseiro terceirizado", 0.1), ("Marmitex", 0.2)],
    "1. Terraplanagem": [("Diesel", 0.6), ("Aluguel de rolo compactador", 0.4), ("Topógrafo terceirizado", 0.1),
                         ("Marmitex", 0.2)],
    "Intervalo": [("Marmitex", 0.5)],
    "2. Estrutura Metálica": [("Perfil metálico", 0.3), ("Parafuso", 0.3), ("Eletrodo", 0.4), ("Diesel", 0.2),
                              ("Aluguel de guindaste", 0.3), ("Empreiteira de solda", 0.1), ("Marmitex", 0.2)],
}

# Faixa de valor (R$) de cada lançamento.
VALORES = {
    "Cimento": (300, 900), "Areia": (200, 600), "Brita": (250, 700), "Vergalhão": (800, 2500),
    "Madeira": (300, 900), "Tijolo": (600, 1800), "Tinta": (300, 1200), "Massa corrida": (150, 500),
    "Perfil metálico": (15000, 40000), "Parafuso": (150, 600), "Eletrodo": (150, 450), "Diesel": (300, 1200),
    "Aluguel de caçamba": (350, 450), "Aluguel de rolo compactador": (600, 900),
    "Aluguel de guindaste": (1800, 2500), "Aluguel de andaime": (120, 250),
    "Empreiteira de solda": (1500, 3000), "Topógrafo terceirizado": (800, 1500),
    "Gesseiro terceirizado": (900, 1800), "Marmitex": (120, 300),
}

# Orçamentos ligados às obras: (obra, nome do projeto, cliente, fração do material orçado já gasta).
# Galpão e Reforma têm o nome do projeto igual ao da obra (o baseline pode ligar pelo nome);
# a Casa tem outro nome (sem obra_id, a ligação é impossível no baseline).
ORCAMENTOS_LIGADOS = [
    ("Galpão Logístico", "Galpão Logístico", "Logística Alfa", 1.15),
    ("Casa Condomínio", "Residência Lote 12", "Condomínio Bela Vista", 0.70),
    ("Reforma Loja Shopping", "Reforma Loja Shopping", "Moda Aurora", 0.95),
]
ORCAMENTOS_SOLTOS = [
    ("Ampliação Escola Municipal", "Prefeitura Municipal", "Em análise"),
    ("Fachada Edifício Aurora", "Condomínio Aurora", "Aprovado"),
    ("Quadra Poliesportiva", "Clube Recreativo", "Recusado"),
]


def sortear_clima(rng):
    manha = rng.choices(*CLIMA)[0]
    tarde = manha if rng.random() < TARDE_REPETE_MANHA else rng.choices(*CLIMA)[0]
    return manha, tarde


def secar(rng, clima):
    return clima if clima in v.CLIMA_SECO else rng.choice(sorted(v.CLIMA_SECO))


def faixa_da_funcao(etapa, funcao):
    fixas, eventuais = EQUIPES[etapa]
    for item in fixas + eventuais:
        if item[0] == funcao:
            return item[1], item[2]
    return 1, 2


def montar_efetivo(rng, etapa, funcoes, horas):
    return [{"funcao": f, "quantidade": rng.randint(*faixa_da_funcao(etapa, f)), "horas": horas} for f in funcoes]


def lancar(rng, catalogo, item):
    return {"item": item, "categoria": catalogo["itens_gasto"][item], "valor": round(rng.uniform(*VALORES[item]), 2)}


def equipamento(rng, catalogo, etapa, nome):
    faixa = next(((q0, q1) for n, _, q0, q1 in EQUIPAMENTOS[etapa] if n == nome), (1, 1))
    return {"nome": nome, "tipo": catalogo["equipamentos"][nome], "quantidade": rng.randint(*faixa)}


def escolher_domingos(rng, dados, obra, furos):
    inicio, fim = v.intervalo_da_obra(dados, obra)
    domingos = [d for d in v.periodo(inicio, fim) if d.weekday() == 6 and (obra, d.isoformat()) not in furos]
    return set(rng.sample(domingos, round(len(domingos) * FRACAO_DOMINGOS)))


def gerar_diario(rng, catalogo, obra, dia, etapa, evento, forcado, dias_secos):
    chave_iso = dia.isoformat()
    manha, tarde = sortear_clima(rng)
    if evento and isinstance(evento["clima"], dict):
        manha, tarde = evento["clima"]["manha"], evento["clima"]["tarde"]
    elif (evento and evento["clima"] == "seco") or (obra, chave_iso) in dias_secos:
        manha, tarde = secar(rng, manha), secar(rng, tarde)
    if forcado:
        manha = forcado["clima"]["algum_periodo"]
    ruim = {manha, tarde} & v.CLIMA_RUIM

    locais = catalogo["compatibilidade"][etapa]["locais"]
    if evento:
        local = evento["local"]
    elif forcado:
        local = forcado["local"]
    elif len(locais) == 1:
        local = locais[0]
    else:
        chance = PROB_INTERIOR_NA_CHUVA if ruim else PROB_INTERIOR_NO_SECO
        local = "Interior" if rng.random() < chance else "Exterior"

    if evento:
        jornada, horas = evento["jornada"], evento["horas"]
    elif forcado:
        jornada, horas = forcado["jornada"], 0
    elif local == "Exterior" and "Tempestade" in (manha, tarde):
        jornada, horas = "parado", v.HORAS_PARADO_MAX
    elif local == "Exterior" and "Chuva" in (manha, tarde):
        jornada, horas = "reduzida", rng.choice(CHUVA_HORAS)
    else:
        jornada, horas = "normal", v.HORAS_NORMAL

    fixas, eventuais = EQUIPES[etapa]
    if evento:
        efetivo = montar_efetivo(rng, etapa, evento["diario"]["efetivo"], horas)
        equipamentos = [equipamento(rng, catalogo, etapa, n) for n in evento["diario"]["equipamentos"]]
        gastos = [lancar(rng, catalogo, g["item"]) for g in evento["diario"]["gastos"]]
    elif jornada == "parado":
        sem_efetivo = forcado is not None or rng.random() < PROB_PARADO_SEM_EFETIVO
        efetivo = [] if sem_efetivo else montar_efetivo(rng, etapa, [f for f, *_ in fixas[:2]], horas)
        equipamentos = []
        locacoes = [i for i, _ in GASTOS[etapa] if catalogo["itens_gasto"][i] == "Locação"]
        gastos = [lancar(rng, catalogo, i) for i in locacoes if rng.random() < 0.5]
    else:
        funcoes = [f for f, *_ in fixas] + [f for f, _, _, chance in eventuais if rng.random() < chance]
        efetivo = montar_efetivo(rng, etapa, funcoes, horas)
        equipamentos = [equipamento(rng, catalogo, etapa, n) for n, chance, *_ in EQUIPAMENTOS[etapa]
                        if rng.random() < chance and not (n in SO_NO_EXTERIOR and local != "Exterior")]
        gastos = [lancar(rng, catalogo, i) for i, chance in GASTOS[etapa] if rng.random() < chance]

    return {"obra": obra, "data": chave_iso, "etapa": etapa, "clima_manha": manha, "clima_tarde": tarde,
            "local": local, "evento": evento["codigo"] if evento else None,
            "efetivo": efetivo, "equipamentos": equipamentos, "gastos": gastos}


def gerar_orcamentos(rng, diarios):
    material = {}
    for d in diarios:
        material[d["obra"]] = material.get(d["obra"], 0) + sum(
            g["valor"] for g in d["gastos"] if g["categoria"] == "Material de Construção")
    orcamentos = []
    for obra, projeto, cliente, fracao_gasta in ORCAMENTOS_LIGADOS:
        custo_material = round(material[obra] / fracao_gasta, -2)
        orcamentos.append({"obra": obra, "nome_projeto": projeto, "cliente": cliente,
                           "custo_material": custo_material, "status": "Convertido em Obra"})
    for projeto, cliente, status in ORCAMENTOS_SOLTOS:
        orcamentos.append({"obra": None, "nome_projeto": projeto, "cliente": cliente,
                           "custo_material": round(rng.uniform(40_000, 200_000), -2), "status": status})
    for o in orcamentos:
        o["custo_mao_de_obra"] = round(o["custo_material"] * rng.uniform(0.6, 0.9), -2)
        o["lucro"] = round((o["custo_material"] + o["custo_mao_de_obra"]) * rng.uniform(0.15, 0.25), 2)
        o["valor_total"] = round(o["custo_material"] + o["custo_mao_de_obra"] + o["lucro"], 2)
    return orcamentos


def gerar(eventos, catalogo, semente=SEMENTE):
    rng = random.Random(semente)
    base = v.Dados(eventos=eventos, catalogo=catalogo, esqueleto={"obras": [], "diarios": []}, rotina=[])
    referencia = base.referencia
    furos = v.datas_sem_diario(base)
    eventos_por_chave = {(e["obra"], e["data"]): e for e in eventos["eventos"]}
    forcados = {(r["obra"], r["data"]): r for r in eventos["restricoes"] if r["tipo"] == "clima_forcado"}
    dias_secos = set()
    for r in eventos["restricoes"]:
        if r["tipo"] == "unico_dia_com_chuva":
            inicio, fim = (date.fromisoformat(x) for x in r["periodo"])
            dias_secos |= {(r["obra"], d.isoformat()) for d in v.periodo(inicio, fim) if d.isoformat() != r["data"]}

    obras, diarios = [], []
    for ref in eventos["obras"]:
        nome = ref["nome"]
        datas = {e["nome"]: (e["inicio"], e["fim"]) for e in ref["etapas"]}
        etapas = []
        for etapa, peso, dias in ETAPAS_PLANEJADAS[nome]:
            inicio, fim = datas.get(etapa, (None, None))
            concluida = fim is not None and date.fromisoformat(fim) < referencia
            etapas.append({"nome": etapa, "peso_percentual": peso, "dias_estimados": dias,
                           "inicio": inicio, "fim": fim, "concluida": concluida})
        primeiro_dia, ultimo_dia = v.intervalo_da_obra(base, nome)
        obras.append({"nome": nome, "endereco": ENDERECOS[nome], "ambiente": ref["ambiente"],
                      "status": ref["status"], "data_inicio": primeiro_dia.isoformat(), "etapas": etapas})

        domingos = escolher_domingos(rng, base, nome, furos)
        for dia in v.periodo(primeiro_dia, ultimo_dia):
            chave = (nome, dia.isoformat())
            evento, forcado = eventos_por_chave.get(chave), forcados.get(chave)
            if chave in furos or (dia.weekday() == 6 and dia not in domingos and not evento and not forcado):
                continue
            etapa = v.etapa_na_data(base, nome, dia)
            diarios.append(gerar_diario(rng, catalogo, nome, dia, etapa, evento, forcado, dias_secos))

    return {"versao": 1, "semente": semente, "referencia": eventos["referencia"],
            "obras": obras, "orcamentos": gerar_orcamentos(rng, diarios), "diarios": diarios}


REGRAS_QUE_DEPENDEM_DA_ROTINA = {v.checar_contagens, v.checar_forma}


def resumir(esqueleto, eventos, catalogo):
    dados = v.Dados(eventos=eventos, catalogo=catalogo, esqueleto=esqueleto, rotina=[])
    print(f"{len(esqueleto['diarios'])} diários")
    for obra in eventos["obras"]:
        ds = [d for d in esqueleto["diarios"] if d["obra"] == obra["nome"]]
        parados = sum(v.jornada(d) == "parado" for d in ds)
        sem_efetivo = sum(not d["efetivo"] for d in ds)
        material = sum(g["valor"] for d in ds for g in d["gastos"] if g["categoria"] == "Material de Construção")
        print(f"  {obra['nome']}: {len(ds)} diários, {parados} parados ({sem_efetivo} sem efetivo), "
              f"material lançado R$ {material:,.2f}")
    estrutura = [d for d in esqueleto["diarios"] if d["etapa"] == v.ETAPA_ESTRUTURA]
    interior = [d for d in estrutura if d["local"] == "Interior"]
    print(f"  Estrutura Metálica: {len(interior)}/{len(estrutura)} dias no interior")
    for o in esqueleto["orcamentos"]:
        print(f"  orçamento {o['nome_projeto']} ({o['status']}): material R$ {o['custo_material']:,.2f}, "
              f"total R$ {o['valor_total']:,.2f}")
    falhas = 0
    for regra in v.CHECAGENS:
        if regra in REGRAS_QUE_DEPENDEM_DA_ROTINA:
            continue
        violacoes = regra(dados)
        falhas += bool(violacoes)
        print(f"  {'ok ' if not violacoes else 'FALHA'} {regra.__name__}" +
              "".join(f"\n        {x}" for x in violacoes[:5]))
    print("Regras que dependem da rotina (contagens, forma) ficam para depois das observações.")
    return falhas


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Gera dados/esqueleto.json.")
    parser.add_argument("--sobrescrever", action="store_true", help="substitui um esqueleto diferente")
    args = parser.parse_args(argumentos)

    eventos = v.ler_json(PASTA / "eventos.json")
    catalogo = v.ler_json(PASTA / "catalogo.json")
    esqueleto = gerar(eventos, catalogo)
    texto = json.dumps(esqueleto, ensure_ascii=False, indent=2) + "\n"

    if SAIDA.is_file() and SAIDA.read_text(encoding="utf-8") != texto and not args.sobrescrever:
        sys.exit(f"{SAIDA} já existe e é diferente do que seria gerado. Use --sobrescrever se for intencional.")
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    print(f"Gravado em {SAIDA}")
    sys.exit(1 if resumir(esqueleto, eventos, catalogo) else 0)


if __name__ == "__main__":
    main()

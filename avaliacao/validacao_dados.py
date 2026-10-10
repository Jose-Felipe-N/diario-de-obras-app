"""Validador dos dados congelados de avaliação (camada 1: determinístico, sem LLM).

Lê quatro arquivos da pasta indicada por DADOS_AVALIACAO_DIR (padrão: dados/):

- eventos.json: eventos plantados, restrições do calendário, obras e etapas de referência.
- catalogo.json: funções, equipamentos, itens de gasto e compatibilidade por etapa.
- esqueleto.json: obras, orçamentos e diários gerados por scripts/gerar_esqueleto.py.
- observacoes_rotina.json: textos de rotina, no máximo um por (obra, data).

Formato de um diário no esqueleto.json:

    {"obra": "Casa Condomínio", "data": "2026-09-09", "etapa": "2. Alvenaria",
     "clima_manha": "Sol", "clima_tarde": "Nublado", "local": "Exterior", "evento": null,
     "efetivo": [{"funcao": "Pedreiro", "quantidade": 3, "horas": 8}],
     "equipamentos": [{"nome": "Betoneira", "tipo": "Maquinário Pesado", "quantidade": 1}],
     "gastos": [{"item": "Tijolo", "categoria": "Material de Construção", "valor": 850.0}]}

A observação de um diário vem do evento (quando "evento" tem um código) ou da rotina;
sem nenhum dos dois, fica vazia.

Cada função checar_* recebe um Dados e devolve a lista de violações. Lista vazia = regra cumprida.
"""

import json
import os
import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

CLIMAS = {"Sol", "Nublado", "Chuva", "Tempestade"}
CLIMA_RUIM = {"Chuva", "Tempestade"}
CLIMA_SECO = {"Sol", "Nublado"}

HORAS_NORMAL = 8
HORAS_PARADO_MAX = 2
HORAS_CHUVA = (4, 6)

TOTAL_DIARIOS = (180, 200)
FRACAO_SEM_OBSERVACAO = (0.22, 0.28)
FRACAO_DOMINGOS_COM_DIARIO_MAX = 0.35
FRACAO_INTERIOR_ESTRUTURA = (0.20, 0.40)
MIN_REFUGIOS_NA_CHUVA = 2
MIN_INTERIOR_SECO = 1
REPETICAO_MAX = 2

TAMANHO_TEXTO = (55, 110)
DIF_MEDIANA_MAX = 15
TOLERANCIA_PROPORCAO = 0.15

ETAPA_INTERVALO = "Intervalo"
ETAPA_ESTRUTURA = "2. Estrutura Metálica"

# Os padrões abaixo rodam sobre texto normalizado: minúsculo e sem acentos.
PALAVRAS_CHUVA = re.compile(
    r"\b(chuv\w*|chov\w*|garoa\w*|temporal\w*|tempestade\w*|trovoad\w*|aguaceiro\w*|raios?)\b")
PALAVRAS_SOL = re.compile(r"\b(sol|ensolarad\w*|calor\w*)\b")
PERIODO_TARDE = re.compile(r"\btarde\b")
PERIODO_MANHA = re.compile(r"\b(manha|cedo)\b")
DIA_PERDIDO = re.compile(
    r"dia perdido|perdemos o dia|dia parado|obra parada|ninguem trabalhou|nao deu pra trabalhar"
    r"|(turma|equipe|pessoal) (foi )?liberad[ao]|foi liberad[ao]")
TEMAS_DE_EVENTO = re.compile(
    r"\b(vaz\w*|acident\w*|ferid\w*|machuc\w*|fornecedor\w*|atras\w*|quebrou|defeito\w*|falt\w*"
    r"|vistori\w*|fiscaliz\w*|vizinh\w*|energia|prumo|atol\w*|client\w*|reclam\w*|proib\w*"
    r"|roub\w*|furt\w*|greve|esquec\w*|err\w*|concessionari\w*|locadora|perdid\w*|nao cheg\w*)")


class DadosAusentes(Exception):
    """Algum arquivo de dados não existe ou não pôde ser lido."""


@dataclass
class Dados:
    eventos: dict
    catalogo: dict
    esqueleto: dict
    rotina: list

    @property
    def referencia(self):
        return date.fromisoformat(self.eventos["referencia"])

    @property
    def diarios(self):
        return self.esqueleto.get("diarios", [])

    @property
    def eventos_por_codigo(self):
        return {e["codigo"]: e for e in self.eventos["eventos"]}

    @property
    def obras_referencia(self):
        return {o["nome"]: o for o in self.eventos["obras"]}

    @property
    def rotina_por_chave(self):
        return {(r["obra"], r["data"]): r["texto"] for r in self.rotina}

    def observacao(self, diario):
        if diario.get("evento"):
            evento = self.eventos_por_codigo.get(diario["evento"])
            return evento["texto"] if evento else ""
        return self.rotina_por_chave.get((diario["obra"], diario["data"]), "")


def ler_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def carregar(pasta=None):
    pasta = Path(pasta or os.environ.get("DADOS_AVALIACAO_DIR") or RAIZ / "dados")
    nomes = ["eventos.json", "catalogo.json", "esqueleto.json", "observacoes_rotina.json"]
    faltando = [n for n in nomes if not (pasta / n).is_file()]
    if faltando:
        raise DadosAusentes(f"arquivos ausentes em {pasta}: {', '.join(faltando)}")
    eventos, catalogo, esqueleto, rotina = (ler_json(pasta / n) for n in nomes)
    return Dados(eventos=eventos, catalogo=catalogo, esqueleto=esqueleto, rotina=rotina)


# ── auxiliares ─────────────────────────────────────────────────────────────────

def normalizar(texto):
    sem_acento = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn").lower()


def frases(texto):
    return [f for f in re.split(r"[.!?]+", texto) if f.strip()]


def rotulo(diario):
    return f"{diario['obra']} {diario['data']}"


def jornada(diario):
    """'parado' (sem efetivo ou até 2 h), 'normal' (todos com 8 h) ou 'reduzida'."""
    horas = [e["horas"] for e in diario["efetivo"]]
    if not horas or max(horas) <= HORAS_PARADO_MAX:
        return "parado"
    if min(horas) >= HORAS_NORMAL:
        return "normal"
    return "reduzida"


def climas(diario):
    return {diario["clima_manha"], diario["clima_tarde"]}


def periodo(inicio, fim):
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def etapa_na_data(dados, obra, dia):
    for etapa in dados.obras_referencia[obra]["etapas"]:
        inicio = date.fromisoformat(etapa["inicio"])
        fim = date.fromisoformat(etapa["fim"]) if etapa["fim"] else dados.referencia - timedelta(days=1)
        if inicio <= dia <= fim:
            return etapa["nome"]
    return None


def intervalo_da_obra(dados, obra):
    etapas = dados.obras_referencia[obra]["etapas"]
    inicio = min(date.fromisoformat(e["inicio"]) for e in etapas)
    fim = max(date.fromisoformat(e["fim"]) if e["fim"] else dados.referencia - timedelta(days=1)
              for e in etapas)
    return inicio, fim


def datas_sem_diario(dados):
    furos = set()
    for r in dados.eventos["restricoes"]:
        if r["tipo"] == "sem_diario":
            obras = dados.obras_referencia if r["obra"] == "*" else [r["obra"]]
            furos |= {(o, r["data"]) for o in obras}
    return furos


def textos_de_rotina(dados):
    return [r["texto"] for r in dados.rotina]


def textos_de_eventos(dados):
    return [e["texto"] for e in dados.eventos["eventos"]]


def proporcoes_de_forma(textos):
    n = len(textos)
    return {
        "mediana_caracteres": statistics.median(len(t) for t in textos),
        "duas_ou_mais_frases": sum(len(frases(t)) >= 2 for t in textos) / n,
        "com_digito": sum(bool(re.search(r"\d", t)) for t in textos) / n,
        "com_virgula": sum("," in t for t in textos) / n,
    }


def alvos_de_forma(eventos_json):
    """Faixas que a rotina precisa respeitar, calculadas a partir dos eventos."""
    base = proporcoes_de_forma([e["texto"] for e in eventos_json["eventos"]])
    alvos = {"tamanho_caracteres": TAMANHO_TEXTO,
             "mediana_caracteres": (base["mediana_caracteres"] - DIF_MEDIANA_MAX,
                                    base["mediana_caracteres"] + DIF_MEDIANA_MAX)}
    for chave in ("duas_ou_mais_frases", "com_digito", "com_virgula"):
        alvos[chave] = (max(0.0, base[chave] - TOLERANCIA_PROPORCAO),
                        min(1.0, base[chave] + TOLERANCIA_PROPORCAO))
    return base, alvos


# ── regras ─────────────────────────────────────────────────────────────────────

def checar_obras_e_etapas(dados):
    v = []
    obras = {o["nome"]: o for o in dados.esqueleto.get("obras", [])}
    for nome, ref in dados.obras_referencia.items():
        obra = obras.get(nome)
        if not obra:
            v.append(f"obra ausente no esqueleto: {nome}")
            continue
        for campo in ("ambiente", "status"):
            if obra.get(campo) != ref[campo]:
                v.append(f"{nome}: {campo} = {obra.get(campo)!r}, esperado {ref[campo]!r}")
        etapas = {e["nome"]: e for e in obra.get("etapas", [])}
        for etapa in ref["etapas"]:
            if etapa["nome"] == ETAPA_INTERVALO:
                continue
            gerada = etapas.get(etapa["nome"])
            if not gerada:
                v.append(f"{nome}: etapa ausente: {etapa['nome']}")
            elif (gerada.get("inicio"), gerada.get("fim")) != (etapa["inicio"], etapa["fim"]):
                v.append(f"{nome}: {etapa['nome']} de {gerada.get('inicio')} a {gerada.get('fim')}, "
                         f"esperado {etapa['inicio']} a {etapa['fim']}")
        soma = sum(e.get("peso_percentual", 0) for e in obra.get("etapas", []))
        if abs(soma - 100) > 0.01:
            v.append(f"{nome}: pesos das etapas somam {soma}, não 100")
    for nome in obras.keys() - dados.obras_referencia.keys():
        v.append(f"obra inesperada no esqueleto: {nome}")
    return v


def checar_calendario(dados):
    """Cada dia útil do período da obra tem diário, salvo os furos; domingos são opcionais."""
    v = []
    contagem = Counter((d["obra"], d["data"]) for d in dados.diarios)
    v += [f"diário duplicado: {o} {d}" for (o, d), n in contagem.items() if n > 1]
    furos = datas_sem_diario(dados)
    for d in dados.diarios:
        if d["obra"] not in dados.obras_referencia:
            v.append(f"{rotulo(d)}: obra desconhecida")
            continue
        dia = date.fromisoformat(d["data"])
        inicio, fim = intervalo_da_obra(dados, d["obra"])
        if not inicio <= dia <= fim:
            v.append(f"{rotulo(d)}: fora do período da obra ({inicio} a {fim})")
        esperada = etapa_na_data(dados, d["obra"], dia)
        if d.get("etapa") != esperada:
            v.append(f"{rotulo(d)}: etapa {d.get('etapa')!r}, esperada {esperada!r}")
    for obra in dados.obras_referencia:
        inicio, fim = intervalo_da_obra(dados, obra)
        domingos = com_diario = 0
        for dia in periodo(inicio, fim):
            chave = (obra, dia.isoformat())
            if dia.weekday() == 6:
                domingos += 1
                com_diario += chave in contagem
            elif chave not in contagem and chave not in furos:
                v.append(f"dia útil sem diário: {obra} {dia}")
        if domingos and com_diario / domingos > FRACAO_DOMINGOS_COM_DIARIO_MAX:
            v.append(f"{obra}: {com_diario} de {domingos} domingos com diário "
                     f"(máximo {FRACAO_DOMINGOS_COM_DIARIO_MAX:.0%})")
    return v


def checar_catalogo(dados):
    v = []
    cat = dados.catalogo
    for d in dados.diarios:
        for e in d["efetivo"]:
            if e["funcao"] not in cat["funcoes"]:
                v.append(f"{rotulo(d)}: função fora do catálogo: {e['funcao']}")
            if e["quantidade"] < 1 or not 0 < e["horas"] <= HORAS_NORMAL:
                v.append(f"{rotulo(d)}: efetivo inválido: {e}")
        for q in d["equipamentos"]:
            tipo = cat["equipamentos"].get(q["nome"])
            if tipo is None:
                v.append(f"{rotulo(d)}: equipamento fora do catálogo: {q['nome']}")
            elif q["tipo"] != tipo:
                v.append(f"{rotulo(d)}: {q['nome']} com tipo {q['tipo']!r}, esperado {tipo!r}")
            if q["quantidade"] < 1:
                v.append(f"{rotulo(d)}: quantidade de equipamento inválida: {q}")
        for g in d["gastos"]:
            if g["categoria"] not in cat["categorias_gasto"]:
                v.append(f"{rotulo(d)}: categoria fora da lista da tela: {g['categoria']!r}")
            categoria = cat["itens_gasto"].get(g["item"])
            if categoria is None:
                v.append(f"{rotulo(d)}: item de gasto fora do catálogo: {g['item']}")
            elif g["categoria"] != categoria:
                v.append(f"{rotulo(d)}: {g['item']} na categoria {g['categoria']!r}, esperado {categoria!r}")
            if g["valor"] <= 0:
                v.append(f"{rotulo(d)}: gasto sem valor positivo: {g}")
    return v


def checar_compatibilidade(dados):
    v = []
    for d in dados.diarios:
        compat = dados.catalogo["compatibilidade"].get(d.get("etapa"))
        if compat is None:
            v.append(f"{rotulo(d)}: etapa sem tabela de compatibilidade: {d.get('etapa')!r}")
            continue
        v += [f"{rotulo(d)}: função {e['funcao']} incompatível com {d['etapa']}"
              for e in d["efetivo"] if e["funcao"] not in compat["funcoes"]]
        v += [f"{rotulo(d)}: equipamento {q['nome']} incompatível com {d['etapa']}"
              for q in d["equipamentos"] if q["nome"] not in compat["equipamentos"]]
        v += [f"{rotulo(d)}: item {g['item']} incompatível com {d['etapa']}"
              for g in d["gastos"] if g["item"] not in compat["itens"]]
    return v


def checar_clima_e_local(dados):
    v = []
    for d in dados.diarios:
        invalidos = climas(d) - CLIMAS
        if invalidos:
            v.append(f"{rotulo(d)}: clima inválido: {sorted(invalidos)}")
        compat = dados.catalogo["compatibilidade"].get(d.get("etapa"), {})
        if d["local"] not in compat.get("locais", []):
            v.append(f"{rotulo(d)}: local {d['local']!r} não permitido em {d.get('etapa')!r}")
    return v


def checar_proporcoes_galpao(dados):
    """Estrutura Metálica: ~30% dos dias no interior, com refúgios na chuva e dias secos."""
    v = []
    estrutura = [d for d in dados.diarios if d.get("etapa") == ETAPA_ESTRUTURA]
    if not estrutura:
        return ["nenhum diário da Estrutura Metálica"]
    interior = [d for d in estrutura if d["local"] == "Interior"]
    fracao = len(interior) / len(estrutura)
    minimo, maximo = FRACAO_INTERIOR_ESTRUTURA
    if not minimo <= fracao <= maximo:
        v.append(f"Estrutura Metálica: {fracao:.0%} dos dias no interior (esperado {minimo:.0%} a {maximo:.0%})")
    refugios = [d for d in interior if climas(d) & CLIMA_RUIM and jornada(d) == "normal"]
    secos = [d for d in interior if climas(d) <= CLIMA_SECO]
    if len(refugios) < MIN_REFUGIOS_NA_CHUVA:
        v.append(f"só {len(refugios)} dia(s) de refúgio no interior durante chuva (mínimo {MIN_REFUGIOS_NA_CHUVA})")
    if len(secos) < MIN_INTERIOR_SECO:
        v.append("nenhum dia seco de pré-montagem no interior")
    return v


def checar_jornada(dados):
    """Clima ruim no exterior reduz a jornada; jornada reduzida só com clima ruim no exterior ou evento."""
    v = []
    eventos = dados.eventos_por_codigo
    for d in dados.diarios:
        j = jornada(d)
        horas_max = max((e["horas"] for e in d["efetivo"]), default=0)
        exterior = d["local"] == "Exterior"
        tempestade = "Tempestade" in climas(d)
        chuva = "Chuva" in climas(d)
        evento = eventos.get(d.get("evento"))
        if exterior and tempestade and j != "parado":
            v.append(f"{rotulo(d)}: tempestade no exterior exige dia parado (jornada {j}, {horas_max} h)")
        elif exterior and chuva and not tempestade:
            if not (j == "reduzida" and HORAS_CHUVA[0] <= horas_max <= HORAS_CHUVA[1]):
                v.append(f"{rotulo(d)}: chuva no exterior exige jornada de {HORAS_CHUVA[0]} a "
                         f"{HORAS_CHUVA[1]} h (jornada {j}, {horas_max} h)")
        explicado = (exterior and (tempestade or chuva)) or (evento and evento["jornada"] == j)
        if j != "normal" and not explicado:
            v.append(f"{rotulo(d)}: jornada {j} sem clima ruim no exterior nem evento que explique")
    return v


def checar_dia_parado(dados):
    """Em dia parado não há equipamento operando nem gasto além de locação."""
    v = []
    for d in dados.diarios:
        if jornada(d) != "parado":
            continue
        if d["equipamentos"]:
            v.append(f"{rotulo(d)}: dia parado com equipamento operando")
        extras = sorted({g["categoria"] for g in d["gastos"]} - {"Locação"})
        if extras:
            v.append(f"{rotulo(d)}: dia parado com gasto de {', '.join(extras)} (só Locação é permitida)")
    return v


def checar_dia_perdido(dados):
    return [f"{rotulo(d)}: observação fala em dia perdido, mas a jornada foi {jornada(d)}"
            for d in dados.diarios
            if DIA_PERDIDO.search(normalizar(dados.observacao(d))) and jornada(d) != "parado"]


def checar_palavras_de_clima(dados):
    """Palavra de clima só quando o diário confirma, no período citado; obra fechada não cita clima."""
    v = []
    ambiente = {n: o["ambiente"] for n, o in dados.obras_referencia.items()}
    for d in dados.diarios:
        texto = normalizar(dados.observacao(d))
        if not texto:
            continue
        if ambiente.get(d["obra"]) == "Fechado":
            if PALAVRAS_CHUVA.search(texto) or PALAVRAS_SOL.search(texto):
                v.append(f"{rotulo(d)}: obra fechada citando clima: {dados.observacao(d)!r}")
            continue
        for frase in frases(texto):
            for padrao, aceitos, nome in ((PALAVRAS_CHUVA, CLIMA_RUIM, "chuva"), (PALAVRAS_SOL, {"Sol"}, "sol")):
                if not padrao.search(frase):
                    continue
                periodos = []
                if PERIODO_MANHA.search(frase):
                    periodos.append(d["clima_manha"])
                if PERIODO_TARDE.search(frase):
                    periodos.append(d["clima_tarde"])
                confirmados = periodos or [d["clima_manha"], d["clima_tarde"]]
                ok = all(c in aceitos for c in confirmados) if periodos else any(c in aceitos for c in confirmados)
                if not ok:
                    v.append(f"{rotulo(d)}: cita {nome} sem confirmação do clima "
                             f"({d['clima_manha']}/{d['clima_tarde']}): {dados.observacao(d)!r}")
    return v


def checar_eventos_plantados(dados):
    v = []
    eventos = dados.eventos["eventos"]
    codigos = [e["codigo"] for e in eventos]
    datas = [e["data"] for e in eventos]
    v += [f"código de evento repetido: {c}" for c, n in Counter(codigos).items() if n > 1]
    v += [f"data de evento repetida: {d}" for d, n in Counter(datas).items() if n > 1]
    furos = datas_sem_diario(dados)
    por_chave = {(d["obra"], d["data"]): d for d in dados.diarios}
    usados = Counter(d["evento"] for d in dados.diarios if d.get("evento"))
    v += [f"evento {c} marcado em {n} diários" for c, n in usados.items() if n > 1]
    v += [f"diário marcado com evento inexistente: {c}" for c in usados if c not in codigos]
    for e in eventos:
        nome = f"{e['codigo']} ({e['obra']} {e['data']})"
        if date.fromisoformat(e["data"]).weekday() == 6:
            v.append(f"{nome}: cai num domingo")
        if (e["obra"], e["data"]) in furos:
            v.append(f"{nome}: cai num furo")
        d = por_chave.get((e["obra"], e["data"]))
        if d is None:
            v.append(f"{nome}: não plantado (sem diário nessa data)")
            continue
        if d.get("evento") != e["codigo"]:
            v.append(f"{nome}: diário não marcado com o evento")
        if d.get("etapa") != e["etapa"]:
            v.append(f"{nome}: etapa {d.get('etapa')!r}, esperada {e['etapa']!r}")
        if d["local"] != e["local"]:
            v.append(f"{nome}: local {d['local']!r}, esperado {e['local']!r}")
        clima = e["clima"]
        if isinstance(clima, dict):
            if (d["clima_manha"], d["clima_tarde"]) != (clima["manha"], clima["tarde"]):
                v.append(f"{nome}: clima {d['clima_manha']}/{d['clima_tarde']}, "
                         f"esperado {clima['manha']}/{clima['tarde']}")
        elif clima == "seco" and not climas(d) <= CLIMA_SECO:
            v.append(f"{nome}: clima deveria ser seco, está {d['clima_manha']}/{d['clima_tarde']}")
        j = jornada(d)
        horas_max = max((x["horas"] for x in d["efetivo"]), default=0)
        if j != e["jornada"]:
            v.append(f"{nome}: jornada {j}, esperada {e['jornada']}")
        elif j == "reduzida" and horas_max != e["horas"]:
            v.append(f"{nome}: jornada de {horas_max} h, esperada {e['horas']} h")
        esperado = e["diario"]
        for campo, gerado in (("efetivo", {x["funcao"] for x in d["efetivo"]}),
                              ("equipamentos", {x["nome"] for x in d["equipamentos"]}),
                              ("gastos", {x["item"] for x in d["gastos"]})):
            alvo = {x["item"] if isinstance(x, dict) else x for x in esperado[campo]}
            if gerado != alvo:
                v.append(f"{nome}: {campo} {sorted(gerado)}, esperado {sorted(alvo)}")
    return v


def checar_restricoes(dados):
    v = []
    por_chave = {(d["obra"], d["data"]): d for d in dados.diarios}
    for r in dados.eventos["restricoes"]:
        tipo = r["tipo"]
        if tipo == "sem_diario":
            obras = dados.obras_referencia if r["obra"] == "*" else [r["obra"]]
            v += [f"{o} {r['data']}: deveria estar sem diário ({r['motivo']})"
                  for o in obras if (o, r["data"]) in por_chave]
        elif tipo == "diario_obrigatorio":
            d = por_chave.get((r["obra"], r["data"]))
            if d is None:
                v.append(f"{r['obra']} {r['data']}: diário obrigatório ausente ({r['motivo']})")
            elif jornada(d) != r["jornada"]:
                v.append(f"{r['obra']} {r['data']}: jornada {jornada(d)}, esperada {r['jornada']}")
        elif tipo == "clima_forcado":
            d = por_chave.get((r["obra"], r["data"]))
            if d is None:
                v.append(f"{r['obra']} {r['data']}: diário com clima forçado ausente ({r['motivo']})")
                continue
            if r["clima"]["algum_periodo"] not in climas(d):
                v.append(f"{r['obra']} {r['data']}: sem {r['clima']['algum_periodo']} ({r['motivo']})")
            if d["local"] != r["local"]:
                v.append(f"{r['obra']} {r['data']}: local {d['local']!r}, esperado {r['local']!r}")
            if jornada(d) != r["jornada"]:
                v.append(f"{r['obra']} {r['data']}: jornada {jornada(d)}, esperada {r['jornada']}")
        elif tipo == "unico_dia_com_chuva":
            inicio, fim = (date.fromisoformat(x) for x in r["periodo"])
            com_chuva = sorted(d["data"] for d in dados.diarios
                               if d["obra"] == r["obra"] and inicio <= date.fromisoformat(d["data"]) <= fim
                               and climas(d) & CLIMA_RUIM)
            if com_chuva != [r["data"]]:
                v.append(f"{r['obra']} {r['periodo'][0]} a {r['periodo'][1]}: dias com chuva {com_chuva}, "
                         f"esperado só {r['data']} ({r['motivo']})")
        else:
            v.append(f"tipo de restrição desconhecido: {tipo}")
    return v


def checar_contagens(dados):
    v = []
    total = len(dados.diarios)
    minimo, maximo = TOTAL_DIARIOS
    if not minimo <= total <= maximo:
        v.append(f"{total} diários (esperado {minimo} a {maximo})")
    if total:
        vazios = sum(not dados.observacao(d).strip() for d in dados.diarios)
        fracao = vazios / total
        minimo, maximo = FRACAO_SEM_OBSERVACAO
        if not minimo <= fracao <= maximo:
            v.append(f"{fracao:.0%} dos diários sem observação (esperado {minimo:.0%} a {maximo:.0%})")
    return v


def checar_rotina(dados):
    """Cada texto de rotina pertence a um diário existente, sem evento, e há no máximo um por diário."""
    v = []
    por_chave = {(d["obra"], d["data"]): d for d in dados.diarios}
    repetidas = Counter((r["obra"], r["data"]) for r in dados.rotina)
    v += [f"rotina com mais de um texto para {o} {d}" for (o, d), n in repetidas.items() if n > 1]
    for r in dados.rotina:
        d = por_chave.get((r["obra"], r["data"]))
        if d is None:
            v.append(f"rotina sem diário correspondente: {r['obra']} {r['data']}")
        elif d.get("evento"):
            v.append(f"rotina num dia de evento ({d['evento']}): {r['obra']} {r['data']}")
        if not r["texto"].strip():
            v.append(f"rotina com texto vazio: {r['obra']} {r['data']} (deixe sem entrada)")
    return v


def checar_repeticao(dados):
    contagem = Counter(normalizar(t).strip() for t in textos_de_rotina(dados))
    return [f"texto de rotina repetido {n} vezes (máximo {REPETICAO_MAX}): {t!r}"
            for t, n in contagem.items() if n > REPETICAO_MAX]


def checar_palavras_de_evento(dados):
    """A rotina não usa palavras-chave dos eventos nem temas típicos de evento."""
    v = []
    chaves = {normalizar(k): e["codigo"] for e in dados.eventos["eventos"] for k in e["palavras_chave"]}
    for r in dados.rotina:
        texto = normalizar(r["texto"])
        v += [f"{r['obra']} {r['data']}: rotina usa palavra-chave do {codigo} ({chave!r})"
              for chave, codigo in chaves.items() if chave in texto]
        tema = TEMAS_DE_EVENTO.search(texto)
        if tema:
            v.append(f"{r['obra']} {r['data']}: rotina usa tema de evento ({tema.group(0)!r}): {r['texto']!r}")
    return v


def checar_forma(dados):
    """Eventos e rotina com a mesma forma, para que os eventos não se destaquem por ela."""
    v = []
    rotina, eventos = textos_de_rotina(dados), textos_de_eventos(dados)
    if not rotina:
        return ["nenhum texto de rotina para comparar com os eventos"]
    minimo, maximo = TAMANHO_TEXTO
    for origem, textos in (("rotina", rotina), ("evento", eventos)):
        v += [f"{origem} com {len(t)} caracteres, fora de {minimo}–{maximo}: {t!r}"
              for t in textos if not minimo <= len(t) <= maximo]
    _, alvos = alvos_de_forma(dados.eventos)
    medida = proporcoes_de_forma(rotina)
    for chave, (baixo, alto) in alvos.items():
        if chave == "tamanho_caracteres":
            continue
        if not baixo <= medida[chave] <= alto:
            v.append(f"rotina: {chave} = {medida[chave]:.2f}, fora do alvo {baixo:.2f}–{alto:.2f}")
    return v


def checar_orcamentos(dados):
    v = []
    orcamentos = dados.esqueleto.get("orcamentos", [])
    if not orcamentos:
        return ["nenhum orçamento no esqueleto"]
    for o in orcamentos:
        nome = o.get("nome_projeto", "?")
        valores = [o["custo_material"], o["custo_mao_de_obra"], o["lucro"]]
        if any(x < 0 for x in valores):
            v.append(f"orçamento {nome}: valor negativo")
        if abs(o["valor_total"] - sum(valores)) > 0.01:
            v.append(f"orçamento {nome}: valor_total {o['valor_total']} diferente de material + mão de obra "
                     f"+ lucro ({sum(valores):.2f}); o lucro é em reais")
    return v


CHECAGENS = [
    checar_obras_e_etapas, checar_calendario, checar_catalogo, checar_compatibilidade,
    checar_clima_e_local, checar_proporcoes_galpao, checar_jornada, checar_dia_parado,
    checar_dia_perdido, checar_palavras_de_clima, checar_eventos_plantados, checar_restricoes,
    checar_contagens, checar_rotina, checar_repeticao, checar_palavras_de_evento, checar_forma,
    checar_orcamentos,
]

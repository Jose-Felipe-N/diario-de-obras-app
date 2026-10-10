"""O conjunto de 20 perguntas está completo, coerente com os eventos e com os números calculados por SQL."""

import json
from collections import Counter

import pytest

from avaliacao import validacao_dados as v
from scripts import calcular_gabarito

CAMPOS_DO_GABARITO = ("pergunta", "modo", "eventos", "obrigatorio", "aceitavel", "proibido")


@pytest.fixture(scope="module")
def conjunto():
    return json.loads(calcular_gabarito.PERGUNTAS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def eventos():
    return v.ler_json(v.RAIZ / "dados" / "eventos.json")


def test_tamanho_ids_e_reservadas(conjunto):
    perguntas = conjunto["perguntas"]
    assert [p["id"] for p in perguntas] == [f"Q{i}" for i in range(1, 21)]
    assert sum(p["reservada"] for p in perguntas) == 4


def test_todos_os_grupos_cobertos(conjunto):
    contagem = Counter(p["grupo"] for p in conjunto["perguntas"])
    assert set(contagem) == set(conjunto["grupos"])


def test_reservadas_em_grupos_diferentes(conjunto):
    grupos = [p["grupo"] for p in conjunto["perguntas"] if p["reservada"]]
    assert len(set(grupos)) == len(grupos)


def test_modos_validos(conjunto, eventos):
    obras = {o["nome"] for o in eventos["obras"]}
    modos = [p["modo"] for p in conjunto["perguntas"]]
    assert set(modos) - {None} <= obras
    assert modos.count(None) == 5


def test_gabarito_completo_e_eventos_existentes(conjunto, eventos):
    codigos = {e["codigo"] for e in eventos["eventos"]}
    for p in conjunto["perguntas"]:
        assert p["obrigatorio"] and p["proibido"], p["id"]
        assert set(p["eventos"]) <= codigos, p["id"]


def test_perguntas_estrela_iguais_ao_eventos_json(conjunto, eventos):
    por_id = {p["id"]: p for p in conjunto["perguntas"]}
    for estrela in eventos["perguntas_estrela"]:
        for campo in CAMPOS_DO_GABARITO:
            assert por_id[estrela["id"]][campo] == estrela[campo], f"{estrela['id']}.{campo}"


def test_valores_batem_com_o_sql(conjunto):
    calculados = calcular_gabarito.calcular(conjunto["referencia"])
    por_id = {p["id"]: p for p in conjunto["perguntas"]}
    for pergunta, valores in calculados.items():
        assert por_id[pergunta]["valores"] == valores, pergunta


def formatos(valor):
    reais = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return {reais, str(int(valor))} if float(valor).is_integer() else {reais}


def test_texto_do_gabarito_cita_os_valores(conjunto):
    for p in conjunto["perguntas"]:
        texto = " ".join(p["obrigatorio"] + p["aceitavel"])
        if p["id"] == "Q19":
            texto += " " + p["turnos_anteriores"][-1]["content"]
        for nome, valor in p.get("valores", {}).items():
            assert any(f in texto for f in formatos(valor)), f"{p['id']}: {nome}={valor} não aparece no gabarito"


def test_diario_da_preparacao_usa_o_catalogo(conjunto):
    catalogo = v.ler_json(v.RAIZ / "dados" / "catalogo.json")
    diario = next(p for p in conjunto["perguntas"] if p["id"] == "Q20")["preparacao"]["criar_diario"]
    assert {e["funcao"] for e in diario["efetivo"]} <= set(catalogo["funcoes"])
    assert all(catalogo["equipamentos"][q["nome"]] == q["tipo"] for q in diario["equipamentos"])

"""O gerador do esqueleto é determinístico e o arquivo versionado é exatamente o que ele produz."""

import pytest

from avaliacao import validacao_dados as v
from scripts import gerar_esqueleto as gerador


@pytest.fixture(scope="module")
def entradas():
    return v.ler_json(gerador.PASTA / "eventos.json"), v.ler_json(gerador.PASTA / "catalogo.json")


@pytest.fixture(scope="module")
def esqueleto(entradas):
    return gerador.gerar(*entradas)


def test_gerar_duas_vezes_produz_o_mesmo_resultado(entradas, esqueleto):
    assert gerador.gerar(*entradas) == esqueleto


def test_arquivo_versionado_e_o_que_o_gerador_produz(esqueleto):
    if not gerador.SAIDA.is_file():
        pytest.skip("dados/esqueleto.json ainda não foi gerado")
    assert v.ler_json(gerador.SAIDA) == esqueleto, "rode scripts/gerar_esqueleto.py --sobrescrever"


def test_esqueleto_passa_nas_regras_que_nao_dependem_da_rotina(entradas, esqueleto):
    dados = v.Dados(eventos=entradas[0], catalogo=entradas[1], esqueleto=esqueleto, rotina=[])
    for regra in v.CHECAGENS:
        if regra not in gerador.REGRAS_QUE_DEPENDEM_DA_ROTINA:
            assert regra(dados) == [], regra.__name__


def test_orcamentos_ligados_tem_a_fracao_de_material_combinada(esqueleto):
    for obra, _, _, fracao in gerador.ORCAMENTOS_LIGADOS:
        gasto = sum(g["valor"] for d in esqueleto["diarios"] if d["obra"] == obra
                    for g in d["gastos"] if g["categoria"] == "Material de Construção")
        orcado = next(o["custo_material"] for o in esqueleto["orcamentos"] if o["obra"] == obra)
        assert gasto / orcado == pytest.approx(fracao, abs=0.01), obra

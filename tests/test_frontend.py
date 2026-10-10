"""O frontend abre sem erro e usa o catálogo único como valor padrão das listas.

Roda o script do Streamlit sem navegador (AppTest). A API não precisa estar no ar:
a página inicial só mostra o aviso de conexão. O menu lateral é um componente
externo que o AppTest não aciona, por isso só a página inicial é exercitada.
"""

import json

import pytest
from streamlit.testing.v1 import AppTest

from avaliacao.validacao_dados import RAIZ


@pytest.fixture(scope="module")
def app():
    return AppTest.from_file(str(RAIZ / "frontend.py"), default_timeout=30).run()


@pytest.fixture(scope="module")
def catalogo():
    with open(RAIZ / "dados" / "catalogo.json", encoding="utf-8") as f:
        return json.load(f)


def test_abre_sem_excecao(app):
    assert [e.value for e in app.exception] == []


def test_listas_padrao_vem_do_catalogo(app, catalogo):
    sessao = app.session_state
    assert sessao["cat_efetivo"] == catalogo["funcoes"]
    assert sessao["cat_equip_tipo"] == catalogo["tipos_equipamento"]
    assert sessao["cat_gastos_categorias"] == catalogo["categorias_gasto"]
    assert sessao["dict_equipamentos"] == catalogo["equipamentos"]
    assert sessao["dict_gastos"] == catalogo["itens_gasto"]


def test_toda_categoria_de_gasto_tem_item(app):
    usadas = set(app.session_state["dict_gastos"].values())
    assert set(app.session_state["cat_gastos_categorias"]) <= usadas

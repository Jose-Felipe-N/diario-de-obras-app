"""Roda cada regra do validador sobre os dados de avaliação.

A pasta vem de DADOS_AVALIACAO_DIR (padrão: dados/). Sem LLM e sem banco: só lê os JSONs.
"""

import pytest

from avaliacao import validacao_dados as v

MAX_LINHAS = 12


@pytest.fixture(scope="session")
def dados():
    try:
        return v.carregar()
    except v.DadosAusentes as erro:
        if set(erro.faltando) <= v.ARQUIVOS_GERADOS:
            pytest.skip(f"dados ainda não gerados ({', '.join(erro.faltando)}); rode scripts/gerar_esqueleto.py")
        pytest.fail(str(erro), pytrace=False)


@pytest.mark.parametrize("regra", v.CHECAGENS, ids=lambda r: r.__name__.removeprefix("checar_"))
def test_regra(dados, regra):
    violacoes = regra(dados)
    resto = f"\n  ... e mais {len(violacoes) - MAX_LINHAS}" if len(violacoes) > MAX_LINHAS else ""
    assert not violacoes, f"{len(violacoes)} violação(ões):\n  " + "\n  ".join(violacoes[:MAX_LINHAS]) + resto

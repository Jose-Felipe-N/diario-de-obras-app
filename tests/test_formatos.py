"""Datas em português na tela."""

from formatos import data_br, data_com_semana, mes_br


def test_formatos_de_data():
    assert data_br("2026-10-07") == "07/10/2026"
    assert data_com_semana("2026-10-07") == "qua, 07/10/2026"
    assert data_com_semana("2026-10-11") == "dom, 11/10/2026"
    assert mes_br("2026-03") == "março de 2026"

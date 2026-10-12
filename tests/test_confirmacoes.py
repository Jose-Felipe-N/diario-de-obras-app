"""Confirmações de exclusão: a obra só sai quando o nome é digitado, e o aviso diz o que será apagado."""

from confirmacoes import nome_confere, resumo_exclusao_diario, resumo_exclusao_obra

OBRA = {"nome": "Casa Condomínio", "diarios": [
    {"data": "2026-09-08", "efetivos": [{"quantidade": 4}, {"quantidade": 2}], "gastos": [{"valor": 1234.5}]},
    {"data": "2026-08-24", "efetivos": [], "gastos": []},
]}


def test_nome_confere_ignora_espacos_e_maiusculas():
    assert nome_confere("  casa condomínio ", "Casa Condomínio")
    assert not nome_confere("Casa", "Casa Condomínio")
    assert not nome_confere("", "Casa Condomínio")
    assert not nome_confere(None, "Casa Condomínio")


def test_resumo_da_obra_conta_os_diarios_e_o_periodo():
    texto = resumo_exclusao_obra(OBRA)
    assert "**2 diários** (de 24/08/2026 a 08/09/2026)" in texto
    assert "Não dá para desfazer" in texto


def test_resumo_da_obra_sem_diarios():
    assert "ainda não tem diários" in resumo_exclusao_obra({"nome": "Nova", "diarios": []})


def test_resumo_do_diario_mostra_data_equipe_e_gastos():
    texto = resumo_exclusao_diario(OBRA["diarios"][0], "Casa Condomínio")
    assert "08/09/2026" in texto and "6 trabalhador(es)" in texto and "R$ 1.234,50" in texto

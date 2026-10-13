"""Adicionar e remover opções das listas editáveis do Novo Diário."""

from opcoes_tela import adicionar_opcao, remover_opcao


def test_item_adicionado_por_engano_pode_ser_removido():
    """O bug antigo: o item adicionado não aparecia para remoção, e remover não mudava a tabela."""
    gastos = {"Cimento": "Material de Construção", "Areia": "Material de Construção"}
    assert adicionar_opcao(gastos, "Cimeto", "Material de Construção")
    assert "Cimeto" in gastos
    assert remover_opcao(gastos, "Cimeto")
    assert gastos == {"Cimento": "Material de Construção", "Areia": "Material de Construção"}


def test_adiciona_em_lista_e_em_dicionario():
    funcoes = ["Servente"]
    equipamentos = {"Betoneira": "Maquinário Pesado"}
    assert adicionar_opcao(funcoes, "Encanador")
    assert adicionar_opcao(equipamentos, "Martelete", "Ferramenta Elétrica")
    assert funcoes == ["Servente", "Encanador"]
    assert equipamentos == {"Betoneira": "Maquinário Pesado", "Martelete": "Ferramenta Elétrica"}


def test_nao_adiciona_vazio_nem_repetido():
    funcoes = ["Servente"]
    assert not adicionar_opcao(funcoes, "")
    assert not adicionar_opcao(funcoes, "   ")
    assert not adicionar_opcao(funcoes, None)
    assert not adicionar_opcao(funcoes, "Servente")
    assert not adicionar_opcao(funcoes, "  Servente ")
    assert funcoes == ["Servente"]


def test_mantem_pelo_menos_uma_opcao():
    funcoes = ["Servente"]
    gastos = {"Cimento": "Material de Construção"}
    assert not remover_opcao(funcoes, "Servente")
    assert not remover_opcao(gastos, "Cimento")
    assert funcoes == ["Servente"] and gastos == {"Cimento": "Material de Construção"}


def test_remover_inexistente_nao_altera():
    gastos = {"Cimento": "Material de Construção", "Areia": "Material de Construção"}
    assert not remover_opcao(gastos, "Brita")
    assert len(gastos) == 2


def test_opcoes_com_inclui_valores_ja_presentes():
    from opcoes_tela import opcoes_com
    linhas = [{"quantidade": 25}, {"quantidade": 3}]
    assert opcoes_com([1, 2, 3], linhas, "quantidade") == [1, 2, 3, 25]
    assert opcoes_com(["Pedreiro"], [{"funcao": "Gesseiro"}], "funcao") == ["Pedreiro", "Gesseiro"]


def test_ultimo_diario_antes_da_data():
    from opcoes_tela import ultimo_diario_antes
    diarios = [{"id": 1, "data": "2026-10-05"}, {"id": 2, "data": "2026-10-07"}, {"id": 3, "data": "2026-10-09"}]
    assert ultimo_diario_antes(diarios, "2026-10-08")["id"] == 2
    assert ultimo_diario_antes(diarios, "2026-10-05") is None

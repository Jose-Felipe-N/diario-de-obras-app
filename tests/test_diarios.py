"""Diário completo gravado de uma vez e exclusão de obra levando os diários junto."""

DIARIO = {
    "data": "2026-10-12", "clima_manha": "Sol", "clima_tarde": "Chuva", "observacoes_gerais": "Choveu à tarde.",
    "local_dia": "Exterior",
    "efetivos": [{"funcao": "Pedreiro", "quantidade": 4, "horas_trabalhadas": 8.0}],
    "equipamentos": [{"nome_item": "Betoneira", "tipo": "Máquina", "quantidade": 1}],
    "gastos": [{"item": "Cimento", "categoria": "Material de Construção", "valor": 350.5}],
}


def criar_obra(cliente, nome="Casa"):
    return cliente.post("/obras/", json={"nome": nome, "ambiente": "Aberto"}).json()["id"]


def diarios_da_obra(cliente, obra_id):
    return next(o for o in cliente.get("/obras/").json() if o["id"] == obra_id)["diarios"]


def test_diario_completo_grava_capa_e_itens(cliente):
    obra_id = criar_obra(cliente)
    resposta = cliente.post("/diarios/completo", json={**DIARIO, "obra_id": obra_id})
    assert resposta.status_code == 200
    [diario] = diarios_da_obra(cliente, obra_id)
    assert diario["observacoes_gerais"] == "Choveu à tarde."
    assert [(e["funcao"], e["quantidade"]) for e in diario["efetivos"]] == [("Pedreiro", 4)]
    assert [e["nome_item"] for e in diario["equipamentos"]] == ["Betoneira"]
    assert [g["valor"] for g in diario["gastos"]] == [350.5]


def test_diario_completo_invalido_nao_grava_nada(cliente):
    obra_id = criar_obra(cliente)
    invalido = {**DIARIO, "obra_id": obra_id, "gastos": [{"item": "Cimento", "categoria": "Material", "valor": "caro"}]}
    assert cliente.post("/diarios/completo", json=invalido).status_code == 422
    assert diarios_da_obra(cliente, obra_id) == []


def test_diario_completo_de_obra_inexistente(cliente):
    assert cliente.post("/diarios/completo", json={**DIARIO, "obra_id": 999}).status_code == 404


def test_excluir_obra_apaga_os_diarios_e_solta_o_orcamento(cliente):
    obra_id = criar_obra(cliente)
    outra = criar_obra(cliente, "Outra")
    for dono in (obra_id, outra):
        assert cliente.post("/diarios/", json={"data": "2026-10-12", "obra_id": dono}).status_code == 200

    orcamento = cliente.post("/orcamentos/", json={"cliente": "C", "nome_projeto": "P", "custo_material": 1,
                                                   "custo_mao_de_obra": 1, "lucro": 0}).json()
    cliente.post(f"/orcamentos/{orcamento['id']}/converter",
                 json={"endereco": "Rua 1", "ambiente": "Aberto", "data_inicio": "2026-10-12"})
    convertida = next(o["id"] for o in cliente.get("/obras/").json() if o["nome"] == "P (C)")

    assert cliente.delete(f"/obras/{obra_id}").status_code == 200
    assert cliente.delete(f"/obras/{convertida}").status_code == 200
    restantes = cliente.get("/diarios/").json()
    assert [d["obra_id"] for d in restantes] == [outra]  # nenhum diário órfão (obra_id nulo)
    [orc] = cliente.get("/orcamentos/").json()
    assert (orc["status"], orc["obra_id"]) == ("Convertido em Obra", None)

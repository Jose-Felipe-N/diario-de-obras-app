"""A migração cria orcamentos.obra_id e liga os orçamentos convertidos à obra criada pelo /converter."""

import sqlite3


def criar_banco_antigo(caminho):
    """Esquema de antes da coluna obra_id."""
    con = sqlite3.connect(caminho)
    con.executescript("""
        CREATE TABLE obras (id INTEGER PRIMARY KEY, nome TEXT NOT NULL);
        CREATE TABLE orcamentos (id INTEGER PRIMARY KEY, cliente TEXT, nome_projeto TEXT, status TEXT);
        INSERT INTO obras VALUES (1, 'Casa 2 (José)'), (2, 'Obra cadastrada à mão');
        INSERT INTO orcamentos VALUES (1, 'José', 'Casa 2', 'Convertido em Obra'),
                                      (2, 'Ana', 'Loja', 'Aprovado'),
                                      (3, 'Rui', 'Galpão', 'Convertido em Obra');
    """)
    con.commit()
    con.close()


def test_cria_coluna_e_liga_os_convertidos(tmp_path):
    from scripts.migrar_orcamento_obra import migrar
    banco = tmp_path / "dev.db"
    criar_banco_antigo(banco)
    migrar(banco)
    con = sqlite3.connect(banco)
    ligacoes = dict(con.execute("SELECT id, obra_id FROM orcamentos"))
    con.close()
    # O orçamento 3 foi convertido, mas a obra "Galpão (Rui)" não existe: fica sem ligação.
    assert ligacoes == {1: 1, 2: None, 3: None}
    assert len(list(tmp_path.glob("dev.antes-orcamento-obra-*.db"))) == 1
    migrar(banco)  # de novo: nada a fazer, sem nova cópia
    assert len(list(tmp_path.glob("dev.antes-orcamento-obra-*.db"))) == 1


def test_converter_liga_o_orcamento_a_obra_criada(cliente):
    orc = cliente.post("/orcamentos/", json={"cliente": "Cliente", "nome_projeto": "Projeto", "custo_material": 1000.0,
                                             "custo_mao_de_obra": 500.0, "lucro": 300.0}).json()
    cliente.post(f"/orcamentos/{orc['id']}/converter",
                 json={"endereco": "Rua A, 1", "ambiente": "Aberto", "data_inicio": "2026-10-05"})
    (obra,) = cliente.get("/obras/").json()
    assert cliente.get("/orcamentos/").json()[0]["obra_id"] == obra["id"]

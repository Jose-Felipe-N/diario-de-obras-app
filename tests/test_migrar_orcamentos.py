"""A migração converte lucro em porcentagem para reais e o status antigo de recusa."""

import sqlite3

import pytest
from sqlalchemy import create_engine

import models
from scripts.migrar_orcamentos import migrar


def criar_banco(caminho, orcamentos):
    engine = create_engine(f"sqlite:///{caminho}")
    models.Base.metadata.create_all(engine)
    engine.dispose()  # no Windows, um arquivo aberto impede a limpeza da pasta temporária
    con = sqlite3.connect(caminho)
    con.executemany(
        "INSERT INTO orcamentos (id, cliente, nome_projeto, custo_material, custo_mao_de_obra, lucro, valor_total, status)"
        " VALUES (?, 'Cliente', ?, ?, ?, ?, ?, ?)", orcamentos)
    con.commit()
    con.close()


def ler(caminho):
    con = sqlite3.connect(caminho)
    linhas = {i: (lucro, total, status)
              for i, lucro, total, status in con.execute("SELECT id, lucro, valor_total, status FROM orcamentos")}
    con.close()
    return linhas


def test_converte_porcentagem_e_status_antigo(tmp_path):
    banco = tmp_path / "dev.db"
    criar_banco(banco, [
        (1, "Lucro em reais", 20000.0, 10000.0, 5000.0, 35000.0, "Aprovado"),
        (2, "Lucro em porcentagem", 30000.0, 5000.0, 30.0, 45500.0, "Convertido em Obra"),
        (3, "Recusado pela tela antiga", 1000.0, 500.0, 300.0, 1800.0, "Obra Negada"),
        (4, "Sem lucro", 1000.0, 500.0, 0.0, 1500.0, "Em análise"),
    ])
    migrar(banco)
    assert ler(banco) == {
        1: (5000.0, 35000.0, "Aprovado"),
        2: (10500.0, 45500.0, "Convertido em Obra"),
        3: (300.0, 1800.0, "Recusado"),
        4: (0.0, 1500.0, "Em análise"),
    }
    assert len(list(tmp_path.glob("dev.antes-orcamentos-*.db"))) == 1


def test_banco_no_formato_novo_nao_muda_nem_gera_copia(tmp_path):
    banco = tmp_path / "dev.db"
    criar_banco(banco, [(1, "Projeto", 20000.0, 10000.0, 5000.0, 35000.0, "Recusado")])
    migrar(banco)
    assert ler(banco) == {1: (5000.0, 35000.0, "Recusado")}
    assert list(tmp_path.glob("dev.antes-orcamentos-*.db")) == []


def test_para_sem_alterar_quando_a_conta_nao_fecha(tmp_path):
    banco = tmp_path / "dev.db"
    criar_banco(banco, [(1, "Conta errada", 20000.0, 10000.0, 5000.0, 99999.0, "Aprovado")])
    with pytest.raises(SystemExit):
        migrar(banco)
    assert ler(banco) == {1: (5000.0, 99999.0, "Aprovado")}

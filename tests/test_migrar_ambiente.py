"""A migração converte rótulos antigos de ambiente e local, e não faz nada num banco já padronizado."""

import sqlite3

from sqlalchemy import create_engine

import models
from scripts.migrar_ambiente import migrar


def criar_banco(caminho, obras, diarios):
    engine = create_engine(f"sqlite:///{caminho}")
    models.Base.metadata.create_all(engine)
    engine.dispose()  # no Windows, um arquivo aberto impede a limpeza da pasta temporária
    con = sqlite3.connect(caminho)
    con.executemany("INSERT INTO obras (id, nome, ambiente) VALUES (?, ?, ?)", obras)
    con.executemany("INSERT INTO diarios_de_obra (id, data, obra_id, local_dia) VALUES (?, '2026-10-01', ?, ?)", diarios)
    con.commit()
    con.close()


def ler(caminho):
    con = sqlite3.connect(caminho)
    obras = dict(con.execute("SELECT id, ambiente FROM obras"))
    diarios = dict(con.execute("SELECT id, local_dia FROM diarios_de_obra"))
    con.close()
    return obras, diarios


def test_converte_rotulos_antigos(tmp_path):
    banco = tmp_path / "dev.db"
    criar_banco(banco,
                obras=[(1, "Casa", "Aberto (Sujeito ao clima)"), (2, "Loja", "Fechado (Coberto)"),
                       (3, "Galpão", "Misto (Aberto e Fechado)"), (4, "Convertida", "Misto")],
                diarios=[(1, 1, "Frente da Obra"), (2, 2, "Frente da Obra"), (3, 3, None),
                         (4, 3, "Interior (Coberto)"), (5, 4, "Exterior (Céu Aberto)")])
    migrar(banco)
    obras, diarios = ler(banco)
    assert obras == {1: "Aberto", 2: "Fechado", 3: "Misto", 4: "Misto"}
    assert diarios == {1: "Exterior", 2: "Interior", 3: "Exterior", 4: "Interior", 5: "Exterior"}
    assert len(list(tmp_path.glob("dev.antes-ambiente-*.db"))) == 1


def test_banco_padronizado_nao_muda_nem_gera_copia(tmp_path):
    banco = tmp_path / "dev.db"
    criar_banco(banco, obras=[(1, "Casa", "Aberto")], diarios=[(1, 1, "Exterior")])
    migrar(banco)
    assert ler(banco) == ({1: "Aberto"}, {1: "Exterior"})
    assert list(tmp_path.glob("dev.antes-ambiente-*.db")) == []

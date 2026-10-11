"""Migração única do banco de desenvolvimento: coluna orcamentos.obra_id.

O create_all do SQLAlchemy não acrescenta colunas a uma tabela que já existe. Este
script cria a coluna e liga os orçamentos já convertidos à obra criada pelo
/converter, que recebe o nome "<projeto> (<cliente>)".

Uso (a partir da raiz do projeto):

    python scripts/migrar_orcamento_obra.py [caminho/do/banco.db]

Faz uma cópia de segurança antes de alterar e pode ser executado mais de uma vez.
"""

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def calcular_mudancas(con):
    colunas = [linha[1] for linha in con.execute("PRAGMA table_info(orcamentos)")]
    criar_coluna = "obra_id" not in colunas
    obras = {nome: obra_id for obra_id, nome in con.execute("SELECT id, nome FROM obras")}
    selecao = ("SELECT id, nome_projeto, cliente FROM orcamentos WHERE status = 'Convertido em Obra'" +
               ("" if criar_coluna else " AND obra_id IS NULL"))
    ligacoes = [(orc_id, obras[f"{projeto} ({cliente})"], f"{projeto} ({cliente})")
                for orc_id, projeto, cliente in con.execute(selecao) if f"{projeto} ({cliente})" in obras]
    return criar_coluna, ligacoes


def migrar(caminho):
    caminho = Path(caminho)
    if not caminho.is_file():
        sys.exit(f"Banco não encontrado: {caminho}")
    con = sqlite3.connect(caminho)
    try:
        criar_coluna, ligacoes = calcular_mudancas(con)
        if not criar_coluna and not ligacoes:
            print("Nada a migrar: a coluna obra_id já existe e os orçamentos convertidos estão ligados.")
            return
        copia = caminho.with_name(f"{caminho.stem}.antes-orcamento-obra-{datetime.now():%Y%m%d-%H%M%S}{caminho.suffix}")
        shutil.copy2(caminho, copia)
        print(f"Cópia de segurança: {copia}")
        if criar_coluna:
            con.execute("ALTER TABLE orcamentos ADD COLUMN obra_id INTEGER REFERENCES obras(id)")
            print("Coluna orcamentos.obra_id criada.")
        for orc_id, obra_id, nome in ligacoes:
            con.execute("UPDATE orcamentos SET obra_id = ? WHERE id = ?", (obra_id, orc_id))
            print(f"orçamento {orc_id} ligado à obra {obra_id} ({nome})")
        con.commit()
        print("Migração concluída.")
    finally:
        con.close()


if __name__ == "__main__":
    migrar(sys.argv[1] if len(sys.argv) > 1 else "diario_obra.db")

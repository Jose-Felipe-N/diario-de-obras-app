"""Migração única do banco de desenvolvimento para os valores padronizados de ambiente e local.

Antes, a mesma informação era gravada de jeitos diferentes: a tela gravava
"Fechado (Coberto)", o /converter gravava "Misto" e o seed gravava "Fechado"
e local "Frente da Obra". A API agora aceita só:

    ambiente: Aberto | Fechado | Misto
    local_dia: Interior | Exterior

O local dos diários antigos sem local válido segue o ambiente da obra
(Aberto -> Exterior, Fechado -> Interior). Para obra Misto não há como saber
onde foi o trabalho; usamos Exterior, porque os diários existentes são de
terraplanagem e montagem de estrutura, feitas ao ar livre.

Uso (a partir da raiz do projeto):

    python scripts/migrar_ambiente.py [caminho/do/banco.db]

Faz uma cópia de segurança antes de alterar e pode ser executado mais de uma vez.
"""

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

AMBIENTE = {
    "Aberto": "Aberto",
    "Aberto (Sujeito ao clima)": "Aberto",
    "Fechado": "Fechado",
    "Fechado (Coberto)": "Fechado",
    "Misto": "Misto",
    "Misto (Aberto e Fechado)": "Misto",
}
LOCAL = {
    "Interior": "Interior",
    "Interior (Coberto)": "Interior",
    "Exterior": "Exterior",
    "Exterior (Céu Aberto)": "Exterior",
}
LOCAL_POR_AMBIENTE = {"Aberto": "Exterior", "Fechado": "Interior", "Misto": "Exterior"}


def calcular_mudancas(con):
    """Devolve as atualizações necessárias sem alterar nada."""
    ambiente_da_obra = {}
    obras = []
    for obra_id, nome, ambiente in con.execute("SELECT id, nome, ambiente FROM obras"):
        novo = AMBIENTE.get(ambiente)
        if novo is None:
            sys.exit(f"Ambiente desconhecido na obra {obra_id} ({nome}): {ambiente!r}. Nada foi alterado.")
        ambiente_da_obra[obra_id] = novo
        if novo != ambiente:
            obras.append((obra_id, nome, ambiente, novo))
    diarios = []
    for diario_id, obra_id, local in con.execute("SELECT id, obra_id, local_dia FROM diarios_de_obra"):
        novo = LOCAL.get(local) or LOCAL_POR_AMBIENTE[ambiente_da_obra.get(obra_id, "Aberto")]
        if novo != local:
            diarios.append((diario_id, local, novo))
    return obras, diarios


def migrar(caminho):
    caminho = Path(caminho)
    if not caminho.is_file():
        sys.exit(f"Banco não encontrado: {caminho}")

    con = sqlite3.connect(caminho)
    try:
        obras, diarios = calcular_mudancas(con)
        if not obras and not diarios:
            print("Nada a migrar: o banco já está padronizado.")
            return

        copia = caminho.with_name(f"{caminho.stem}.antes-ambiente-{datetime.now():%Y%m%d-%H%M%S}{caminho.suffix}")
        shutil.copy2(caminho, copia)
        print(f"Cópia de segurança: {copia}")

        for obra_id, nome, antes, depois in obras:
            con.execute("UPDATE obras SET ambiente = ? WHERE id = ?", (depois, obra_id))
            print(f"obra {obra_id} ({nome}): ambiente {antes!r} -> {depois!r}")
        resumo = {}
        for diario_id, antes, depois in diarios:
            con.execute("UPDATE diarios_de_obra SET local_dia = ? WHERE id = ?", (depois, diario_id))
            resumo[(antes, depois)] = resumo.get((antes, depois), 0) + 1
        for (antes, depois), n in sorted(resumo.items(), key=str):
            print(f"{n} diário(s): local {antes!r} -> {depois!r}")
        con.commit()
        print("Migração concluída.")
    finally:
        con.close()


if __name__ == "__main__":
    migrar(sys.argv[1] if len(sys.argv) > 1 else "diario_obra.db")

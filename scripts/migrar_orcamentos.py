"""Migração única do banco de desenvolvimento para o novo formato dos orçamentos.

Antes, o campo lucro tinha dois significados: a tela gravava a porcentagem de
markup (ex.: 30) e calculava o total como custo × 1,30; o seed gravava reais
(ex.: 9919.69) e somava. Agora o lucro é sempre em reais e o total é
material + mão de obra + lucro, calculado pelo servidor.

Um orçamento com lucro em porcentagem é reconhecido pela conta: o total bate
com custo × (1 + lucro/100) e não com custo + lucro. O lucro vira reais e o
total não muda.

O status "Obra Negada", gravado pela tela antiga, vira "Recusado".

Uso (a partir da raiz do projeto):

    python scripts/migrar_orcamentos.py [caminho/do/banco.db]

Faz uma cópia de segurança antes de alterar e pode ser executado mais de uma vez.
"""

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

STATUS = {
    "Em análise": "Em análise",
    "Aprovado": "Aprovado",
    "Recusado": "Recusado",
    "Obra Negada": "Recusado",
    "Convertido em Obra": "Convertido em Obra",
}
TOLERANCIA = 0.01


def calcular_mudancas(con):
    """Devolve as atualizações necessárias sem alterar nada."""
    mudancas = []
    linhas = con.execute(
        "SELECT id, nome_projeto, custo_material, custo_mao_de_obra, lucro, valor_total, status FROM orcamentos")
    for orc_id, nome, material, mao, lucro, total, status in linhas:
        novo_status = STATUS.get(status)
        if novo_status is None:
            sys.exit(f"Status desconhecido no orçamento {orc_id} ({nome}): {status!r}. Nada foi alterado.")
        custo = material + mao
        if abs(total - (custo + lucro)) <= TOLERANCIA:
            novo_lucro = lucro
        elif abs(total - custo * (1 + lucro / 100)) <= TOLERANCIA:
            novo_lucro = round(custo * lucro / 100, 2)
        else:
            sys.exit(f"Orçamento {orc_id} ({nome}): o total {total} não fecha nem com lucro em reais "
                     f"nem em porcentagem. Nada foi alterado.")
        if (novo_lucro, novo_status) != (lucro, status):
            mudancas.append((orc_id, nome, lucro, novo_lucro, status, novo_status, round(custo + novo_lucro, 2)))
    return mudancas


def migrar(caminho):
    caminho = Path(caminho)
    if not caminho.is_file():
        sys.exit(f"Banco não encontrado: {caminho}")

    con = sqlite3.connect(caminho)
    try:
        mudancas = calcular_mudancas(con)
        if not mudancas:
            print("Nada a migrar: os orçamentos já estão no formato novo.")
            return

        copia = caminho.with_name(f"{caminho.stem}.antes-orcamentos-{datetime.now():%Y%m%d-%H%M%S}{caminho.suffix}")
        shutil.copy2(caminho, copia)
        print(f"Cópia de segurança: {copia}")

        for orc_id, nome, lucro, novo_lucro, status, novo_status, total in mudancas:
            con.execute("UPDATE orcamentos SET lucro = ?, valor_total = ?, status = ? WHERE id = ?",
                        (novo_lucro, total, novo_status, orc_id))
            if novo_lucro != lucro:
                print(f"orçamento {orc_id} ({nome}): lucro {lucro}% -> R$ {novo_lucro:.2f} (total R$ {total:.2f})")
            if novo_status != status:
                print(f"orçamento {orc_id} ({nome}): status {status!r} -> {novo_status!r}")
        con.commit()
        print("Migração concluída.")
    finally:
        con.close()


if __name__ == "__main__":
    migrar(sys.argv[1] if len(sys.argv) > 1 else "diario_obra.db")

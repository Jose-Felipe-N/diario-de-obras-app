"""Popula o banco com os dados fictícios de avaliação (pasta dados/).

São 3 obras, 189 diários e 6 orçamentos, com datas de junho a outubro de 2026
("hoje" nesses dados é 08/10/2026). O banco usado é o do DIARIO_DB_PATH
(padrão: diario_obra.db).

⚠️ Apaga e recria o banco. Se ele já tiver obras, pede confirmação antes.

Uso:

    python seed.py          # pergunta antes de apagar um banco com dados
    python seed.py --sim    # não pergunta
"""

import argparse

from sqlalchemy import inspect, select, func

import database
import models
from avaliacao.carga import carregar_banco


def obras_existentes(engine):
    if not inspect(engine).has_table(models.Obra.__tablename__):
        return 0
    with engine.connect() as conexao:
        return conexao.execute(select(func.count()).select_from(models.Obra)).scalar_one()


def main(argumentos=None, engine=None, perguntar=input):
    parser = argparse.ArgumentParser(description="Carrega os dados de avaliação no banco (apaga o banco antes).")
    parser.add_argument("--sim", action="store_true", help="não pede confirmação antes de apagar o banco")
    args = parser.parse_args(argumentos)
    engine = engine or database.engine

    existentes = obras_existentes(engine)
    if existentes and not args.sim:
        resposta = perguntar(f"O banco {engine.url.database} tem {existentes} obra(s). "
                             "Apagar tudo e carregar os dados de avaliação? [s/N] ")
        if resposta.strip().lower() not in ("s", "sim"):
            print("Nada foi alterado.")
            return False

    resumo = carregar_banco(engine)
    print(f"Banco {engine.url.database} carregado: {resumo['obras']} obras, {resumo['diarios']} diários, "
          f"{resumo['orcamentos']} orçamentos (data de referência dos dados: {resumo['referencia']}).")
    return True


if __name__ == "__main__":
    main()

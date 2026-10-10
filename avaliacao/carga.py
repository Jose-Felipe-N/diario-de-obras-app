"""Carrega os dados congelados de avaliação (pasta dados/) num banco.

Usado pelo seed.py, para desenvolvimento e demonstração, e pelo script de avaliação,
para montar o banco da medição. Os dois passam por este mesmo código, então os
dados da demonstração e os da medição são garantidamente iguais.
"""

from datetime import date

from sqlalchemy.orm import sessionmaker

import models
from avaliacao import validacao_dados as v


def _data(texto):
    return date.fromisoformat(texto) if texto else None


def carregar_banco(engine, pasta=None):
    """Apaga e recria as tabelas do banco e grava os dados de avaliação. Devolve um resumo."""
    dados = v.carregar(pasta)
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    sessao = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with sessao() as db:
        obras = {}
        for o in dados.esqueleto["obras"]:
            obra = models.Obra(nome=o["nome"], endereco=o["endereco"], data_inicio=_data(o["data_inicio"]),
                               status=o["status"], ambiente=o["ambiente"])
            obra.etapas = [models.EtapaObra(nome_etapa=e["nome"], peso_percentual=e["peso_percentual"],
                                            dias_estimados=e["dias_estimados"], data_inicio_real=_data(e["inicio"]),
                                            data_fim_real=_data(e["fim"]), concluida=e["concluida"])
                           for e in o["etapas"]]
            db.add(obra)
            obras[o["nome"]] = obra

        for d in dados.diarios:
            diario = models.DiarioDeObra(
                data=_data(d["data"]), clima_manha=d["clima_manha"], clima_tarde=d["clima_tarde"],
                observacoes_gerais=dados.observacao(d), local_dia=d["local"], obra=obras[d["obra"]])
            diario.efetivos = [models.Efetivo(funcao=e["funcao"], quantidade=e["quantidade"],
                                              horas_trabalhadas=e["horas"]) for e in d["efetivo"]]
            diario.equipamentos = [models.Equipamento(nome_item=q["nome"], tipo=q["tipo"],
                                                      quantidade=q["quantidade"]) for q in d["equipamentos"]]
            diario.gastos = [models.Gasto(item=g["item"], categoria=g["categoria"], valor=g["valor"])
                             for g in d["gastos"]]
            db.add(diario)

        # A ligação orçamento-obra fica só no JSON até a etapa 4 (coluna obra_id).
        for o in dados.esqueleto["orcamentos"]:
            db.add(models.orcamento(cliente=o["cliente"], nome_projeto=o["nome_projeto"],
                                    custo_material=o["custo_material"], custo_mao_de_obra=o["custo_mao_de_obra"],
                                    lucro=o["lucro"], valor_total=o["valor_total"], status=o["status"]))
        db.commit()

    return {"obras": len(obras), "diarios": len(dados.diarios), "orcamentos": len(dados.esqueleto["orcamentos"]),
            "referencia": dados.eventos["referencia"]}

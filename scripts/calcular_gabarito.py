"""Calcula por SQL os números do gabarito (campo 'valores' de dados/perguntas.json).

Carrega os dados de avaliação num banco em memória e roda uma consulta por valor.
Assim, a resposta certa das perguntas numéricas sai dos dados, não de uma conta manual.

Uso (a partir da raiz do projeto):

    python scripts/calcular_gabarito.py              # confere e mostra diferenças
    python scripts/calcular_gabarito.py --atualizar  # grava os valores calculados
"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from avaliacao.carga import carregar_banco  # noqa: E402

PERGUNTAS = RAIZ / "dados" / "perguntas.json"

GASTOS = """SELECT round(coalesce(sum(g.valor), 0), 2) FROM gastos g
            JOIN diarios_de_obra d ON d.id = g.diario_id JOIN obras o ON o.id = d.obra_id
            WHERE o.nome = :obra"""
MATERIAL = GASTOS + " AND g.categoria = 'Material de Construção'"
MATERIAL_SEMANA_PASSADA = MATERIAL + " AND d.data BETWEEN '2026-09-28' AND '2026-10-04'"
ETAPA = """SELECT {expressao} FROM etapas_obra e JOIN obras o ON o.id = e.obra_id
           WHERE o.nome = :obra AND e.nome_etapa = :etapa"""
DIAS_ATE_HOJE = ETAPA.format(expressao="CAST(julianday(:referencia) - julianday(e.data_inicio_real) AS INTEGER)")
DIAS_CONCLUIDA = ETAPA.format(expressao="CAST(julianday(e.data_fim_real) - julianday(e.data_inicio_real) AS INTEGER)")
ESTIMADOS = ETAPA.format(expressao="e.dias_estimados")
ORCADO = "SELECT custo_material FROM orcamentos WHERE nome_projeto = :projeto"

CASA, GALPAO = {"obra": "Casa Condomínio"}, {"obra": "Galpão Logístico"}
ESTRUTURA = {**GALPAO, "etapa": "2. Estrutura Metálica"}
TERRAPLANAGEM = {**GALPAO, "etapa": "1. Terraplanagem"}
ALVENARIA = {**CASA, "etapa": "2. Alvenaria"}

# id da pergunta -> nome do valor -> (consulta, parâmetros)
CONSULTAS = {
    "Q9": {
        "mao_de_obra_externa": (GASTOS + " AND g.categoria = 'Mão de Obra Externa'", CASA),
        "homens_hora_equipe_propria": ("""SELECT sum(e.quantidade * e.horas_trabalhadas) FROM efetivos e
                                          JOIN diarios_de_obra d ON d.id = e.diario_id
                                          JOIN obras o ON o.id = d.obra_id WHERE o.nome = :obra""", CASA),
    },
    "Q11": {
        "cimento": (GASTOS + " AND g.item = 'Cimento'", CASA),
        "compras_de_cimento": ("""SELECT count(*) FROM gastos g JOIN diarios_de_obra d ON d.id = g.diario_id
                                  JOIN obras o ON o.id = d.obra_id WHERE o.nome = :obra AND g.item = 'Cimento'""", CASA),
    },
    "Q13": {
        "estrutura_dias": (DIAS_ATE_HOJE, ESTRUTURA), "estrutura_estimados": (ESTIMADOS, ESTRUTURA),
        "terraplanagem_dias": (DIAS_CONCLUIDA, TERRAPLANAGEM), "terraplanagem_estimados": (ESTIMADOS, TERRAPLANAGEM),
        "alvenaria_dias": (DIAS_ATE_HOJE, ALVENARIA), "alvenaria_estimados": (ESTIMADOS, ALVENARIA),
    },
    "Q14": {"material_lancado": (MATERIAL, GALPAO), "material_orcado": (ORCADO, {"projeto": "Galpão Logístico"})},
    "Q15": {"material_lancado": (MATERIAL, CASA), "material_orcado": (ORCADO, {"projeto": "Residência Lote 12"})},
    "Q19": {"casa": (MATERIAL_SEMANA_PASSADA, CASA), "galpao": (MATERIAL_SEMANA_PASSADA, GALPAO)},
}


def calcular(referencia):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    carregar_banco(engine)
    valores = {}
    with engine.connect() as conexao:
        for pergunta, consultas in CONSULTAS.items():
            valores[pergunta] = {nome: conexao.execute(text(sql), {**parametros, "referencia": referencia}).scalar_one()
                                 for nome, (sql, parametros) in consultas.items()}
    return valores


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Calcula por SQL os números do gabarito.")
    parser.add_argument("--atualizar", action="store_true", help="grava os valores calculados em perguntas.json")
    args = parser.parse_args(argumentos)

    conjunto = json.loads(PERGUNTAS.read_text(encoding="utf-8"))
    calculados = calcular(conjunto["referencia"])
    diferencas = 0
    for p in conjunto["perguntas"]:
        if p["id"] not in calculados:
            continue
        if p.get("valores") != calculados[p["id"]]:
            diferencas += 1
            print(f"{p['id']}: arquivo {p.get('valores')} | calculado {calculados[p['id']]}")
            p["valores"] = calculados[p["id"]]
    if not diferencas:
        print("Todos os valores do gabarito batem com os dados.")
    elif args.atualizar:
        PERGUNTAS.write_text(json.dumps(conjunto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{diferencas} pergunta(s) atualizada(s). Revise os textos do gabarito que citam esses números.")
    sys.exit(1 if diferencas and not args.atualizar else 0)


if __name__ == "__main__":
    main()

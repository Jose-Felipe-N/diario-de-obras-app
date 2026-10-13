#!/usr/bin/env bash
# Medição preliminar: subconjunto de 10 perguntas, antes e depois, no nível gratuito.
#
# 1. Completa o "antes" no worktree da tag baseline (../diario-baseline).
# 2. Roda a Q4 no "depois" como pergunta-teste; para tudo se ela falhar por erro do
#    assistente (HTTP 500 ou 502). Falha por sobrecarga do Google (503) não para.
# 3. Mede o restante do "depois".
#
# Quando a cota diária acaba, o avaliar.py para sem gravar a pergunta; rode este
# script de novo depois que a cota voltar (04h ou 05h de Brasília) e ele continua.
#
# Uso (Git Bash, a partir da raiz do projeto):
#     bash scripts/medicao_preliminar.sh            # começa agora
#     bash scripts/medicao_preliminar.sh 04:05      # espera até 04:05 (horário local) para começar
set -euo pipefail

PRINCIPAL="$(cd "$(dirname "$0")/.." && pwd)"
BASELINE="$(cd "$PRINCIPAL/.." && pwd)/diario-baseline"
PY="$PRINCIPAL/venv/Scripts/python.exe"
RESULTADOS="$PRINCIPAL/avaliacao/resultados"
RESULTADOS_PY="$(cygpath -m "$RESULTADOS")"  # caminho que o Python do Windows entende
SUBCONJUNTO="Q1 Q2 Q4 Q5 Q6 Q9 Q13 Q15 Q16 Q18"
ANTES_FALTANDO="Q9 Q13 Q15 Q16 Q18"
# GEMINI_MODEL para o código da tag baseline; AVALIACAO_MODELO para o código atual.
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 GEMINI_MODEL=gemini-3.8-flash AVALIACAO_MODELO=gemini-3.8-flash DIARIO_DB_PATH=avaliacao/eval.db

if [ $# -ge 1 ]; then
    espera=$("$PY" -c "
from datetime import datetime, timedelta
alvo = datetime.combine(datetime.now().date(), datetime.strptime('$1', '%H:%M').time())
alvo += timedelta(days=1) if alvo <= datetime.now() else timedelta()
print(int((alvo - datetime.now()).total_seconds()))")
    echo "Esperando ${espera}s até $1..."
    sleep "$espera"
fi

echo "== 1. Antes (worktree da tag baseline): $ANTES_FALTANDO"
(cd "$BASELINE" && "$PY" -m avaliacao.avaliar --rotulo antes --saida "$RESULTADOS" --ids $ANTES_FALTANDO)

echo "== 2. Depois: pergunta-teste Q4"
(cd "$PRINCIPAL" && "$PY" -m avaliacao.avaliar --rotulo depois --ids Q4)
situacao=$("$PY" -c "
import json, sys
linhas = [json.loads(l) for l in open(r'$RESULTADOS_PY/depois.jsonl', encoding='utf-8')] if __import__('os').path.exists(r'$RESULTADOS_PY/depois.jsonl') else []
q4 = [l for l in linhas if l['id'] == 'Q4']
print('sem_resposta' if not q4 else 'ok' if q4[-1]['status'] == 'ok' else f\"erro_{q4[-1]['http']}\")")
echo "   Q4: $situacao"
if [ "$situacao" = "erro_500" ] || [ "$situacao" = "erro_502" ]; then
    echo "A pergunta-teste falhou por erro do assistente. Parando para não gastar a cota."
    exit 1
fi

echo "== 3. Depois: restante do subconjunto"
(cd "$PRINCIPAL" && "$PY" -m avaliacao.avaliar --rotulo depois --ids $SUBCONJUNTO)
echo "Fim. Respostas em $RESULTADOS (antes.jsonl e depois.jsonl)."

"""Configuração do projeto, lida de variáveis de ambiente ou do arquivo .env.

Uma variável definida no terminal tem prioridade sobre o .env. Sem nenhuma das
duas, valem os padrões abaixo, que reproduzem o comportamento de antes.
"""

import logging
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent

load_dotenv(RAIZ / ".env")

# Chave da API do Gemini.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Modelo usado pelo Analista IA no app. Precisa ser da família Gemini 3: o assistente manda as
# ferramentas e o schema da resposta na mesma chamada, e o Gemini 2.5 recusa essa combinação (erro 400).
# O Flash Lite tem 500 requisições por dia no nível gratuito (o 3.8 Flash tem 20). A avaliação
# não usa esta variável: ela mede sempre com o modelo fixo em avaliacao/avaliar.py.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Arquivo SQLite. Caminho relativo é resolvido a partir da pasta do projeto,
# para não criar um banco vazio quando o app é iniciado de outra pasta.
DIARIO_DB_PATH = RAIZ / os.getenv("DIARIO_DB_PATH", "diario_obra.db")

# Endereço da API chamado pelo frontend.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

# Arquivo do contador de cota do Gemini. Fica fora do projeto para ser o mesmo
# em todas as cópias (a pasta principal e o worktree do baseline).
COTA_GEMINI_ARQUIVO = Path(os.getenv("COTA_GEMINI_ARQUIVO", Path.home() / ".diario_obras" / "cota_gemini.json"))

# Pasta do índice vetorial (ChromaDB) das observações dos diários. Cada banco tem a sua coleção.
CHROMA_DIR = RAIZ / os.getenv("CHROMA_DIR", "chroma")

# Avaliações 👍/👎 das respostas do Analista IA (uma por linha, JSON). Respostas com 👎 são
# candidatas a virar perguntas novas do conjunto de avaliação.
FEEDBACK_ARQUIVO = RAIZ / os.getenv("FEEDBACK_ARQUIVO", "feedback/avaliacoes.jsonl")

# Como as chamadas são anotadas no contador: "desenvolvimento" (padrão) ou "avaliacao".
COTA_ORIGEM = os.getenv("COTA_ORIGEM", "desenvolvimento")

# "gratuito" (padrão) aplica os limites diários do nível gratuito; "pago" só conta as chamadas.
COTA_NIVEL = os.getenv("COTA_NIVEL", "gratuito")

# Data tratada como "hoje" pelo assistente e pelo painel. Só para a avaliação e para
# demonstrações com os dados de avaliação (2026-10-08); nunca coloque no .env do app.
DATA_REFERENCIA = date.fromisoformat(os.environ["DATA_REFERENCIA"]) if os.getenv("DATA_REFERENCIA") else None
if DATA_REFERENCIA:
    logging.getLogger(__name__).warning("DATA_REFERENCIA definida: 'hoje' é %s, não a data real.", DATA_REFERENCIA)


def hoje():
    """A data de referência, se definida; senão, a data real."""
    return DATA_REFERENCIA or date.today()

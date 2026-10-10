"""Configuração do projeto, lida de variáveis de ambiente ou do arquivo .env.

Uma variável definida no terminal tem prioridade sobre o .env. Sem nenhuma das
duas, valem os padrões abaixo, que reproduzem o comportamento de antes.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent

load_dotenv(RAIZ / ".env")

# Chave da API do Gemini.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Modelo usado pelo Analista IA.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Arquivo SQLite. Caminho relativo é resolvido a partir da pasta do projeto,
# para não criar um banco vazio quando o app é iniciado de outra pasta.
DIARIO_DB_PATH = RAIZ / os.getenv("DIARIO_DB_PATH", "diario_obra.db")

# Endereço da API chamado pelo frontend.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

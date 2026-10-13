"""Configuração por variáveis de ambiente, com padrões iguais aos valores de antes.

Cada caso roda num processo separado, iniciado de outra pasta, porque o config é
lido uma única vez, quando o módulo é importado.
"""

import json
import os
import subprocess
import sys

import pytest
from dotenv import dotenv_values

from config import RAIZ

LER_CONFIG = """
import json, config, database
print(json.dumps({"banco": database.engine.url.database, "modelo": config.GEMINI_MODEL, "api": config.API_URL}))
"""


def ler_config(pasta, **variaveis):
    ambiente = {k: v for k, v in os.environ.items()
                if k not in ("DIARIO_DB_PATH", "GEMINI_MODEL", "API_URL")}
    ambiente.update(variaveis, PYTHONPATH=str(RAIZ))
    saida = subprocess.run([sys.executable, "-c", LER_CONFIG], cwd=pasta, env=ambiente,
                           capture_output=True, text=True, check=True)
    return json.loads(saida.stdout)


def test_variaveis_de_ambiente_tem_prioridade(tmp_path):
    banco = tmp_path / "eval.db"
    lido = ler_config(tmp_path, DIARIO_DB_PATH=str(banco), GEMINI_MODEL="modelo-teste",
                      API_URL="http://127.0.0.1:8001/")
    assert lido == {"banco": str(banco), "modelo": "modelo-teste", "api": "http://127.0.0.1:8001"}


def test_caminho_relativo_do_banco_e_resolvido_na_pasta_do_projeto(tmp_path):
    lido = ler_config(tmp_path, DIARIO_DB_PATH="dados/eval.db")
    assert lido["banco"] == str(RAIZ / "dados" / "eval.db")


def test_padroes_reproduzem_o_comportamento_anterior(tmp_path):
    definidas = dotenv_values(RAIZ / ".env").keys() & {"DIARIO_DB_PATH", "GEMINI_MODEL", "API_URL"}
    if definidas:
        pytest.skip(f"o .env local define {sorted(definidas)}; os padrões não se aplicam")
    lido = ler_config(tmp_path)
    assert lido == {"banco": str(RAIZ / "diario_obra.db"), "modelo": "gemini-3.5-flash-lite",
                    "api": "http://127.0.0.1:8000"}


def test_nenhum_endereco_fixo_no_frontend():
    assert "127.0.0.1" not in (RAIZ / "frontend.py").read_text(encoding="utf-8")


def test_get_db_definido_so_no_database():
    copias = [p.name for p in (RAIZ / "routers").glob("*.py") if "def get_db" in p.read_text(encoding="utf-8")]
    assert copias == []

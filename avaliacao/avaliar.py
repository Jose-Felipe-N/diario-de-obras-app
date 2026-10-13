"""Roda o conjunto de avaliação contra o Analista IA e grava as respostas em JSONL.

Cada pergunta de dados/perguntas.json vira uma chamada a POST /ia/chat, feita no
próprio processo (TestClient), num banco de avaliação separado. O banco é recarregado
com os dados congelados antes da rodada e depois de cada pergunta que cria dados.

Uso (a partir da raiz do projeto; o banco nunca pode ser o diario_obra.db):

    DIARIO_DB_PATH=avaliacao/eval.db python -m avaliacao.avaliar --rotulo antes

O modelo é sempre o da medição (MODELO_PADRAO), mesmo que o .env do app defina GEMINI_MODEL:
trocar o modelo no meio invalidaria a comparação com o "antes". Para medir outro modelo de
propósito, use AVALIACAO_MODELO=...

Com a chave paga (sem limite diário; contada num contador separado):

    GEMINI_API_KEY_AVALIACAO=... DIARIO_DB_PATH=... python -m avaliacao.avaliar --rotulo antes

A saída é <saida>/<rotulo>.jsonl. Rodar de novo continua de onde parou: perguntas já
respondidas são puladas. Quando a cota acaba, o script para sem gravar a pergunta.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
import cota
import database
import gemini
import models
from avaliacao.carga import carregar_banco
from main import app

RAIZ = config.RAIZ
PERGUNTAS = RAIZ / "dados" / "perguntas.json"
ARQUIVOS_DE_DADOS = ["esqueleto.json", "eventos.json", "observacoes_rotina.json", "catalogo.json"]
BANCO_DE_DEV = (RAIZ / "diario_obra.db").resolve()
MODELO_PADRAO = "gemini-3.8-flash"

ERROS_TEMPORARIOS = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500", "INTERNAL", "DEADLINE")
SINAIS_DE_COTA_ESGOTADA = ("Limite diário do assistente", "A avaliação já usou", "Hoje é dia de medição")
ESPERAS_APOS_ERRO = [15, 30, 60, 120]
NUMERO = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")


class ParadaPorCota(Exception):
    """A cota acabou; a pergunta não foi gravada e pode ser refeita depois."""


def hash_canonico(*caminhos):
    h = hashlib.sha256()
    for caminho in caminhos:
        texto = Path(caminho).read_text(encoding="utf-8")
        if str(caminho).endswith(".json"):
            texto = json.dumps(json.loads(texto), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        h.update(texto.replace("\r\n", "\n").encode("utf-8"))
    return h.hexdigest()[:16]


def commit_atual():
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
        sujo = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
        return f"{sha}{'+alterado' if sujo else ''}"
    except OSError:
        return None


def caminho_do_banco():
    valor = os.getenv("DIARIO_DB_PATH")
    if not valor:
        sys.exit("Defina DIARIO_DB_PATH com um banco só para a avaliação (ex.: avaliacao/eval.db).")
    caminho = (RAIZ / valor).resolve()
    if caminho == BANCO_DE_DEV:
        sys.exit(f"DIARIO_DB_PATH aponta para o banco de desenvolvimento ({caminho}). Use outro arquivo.")
    return caminho


@contextmanager
def configuracao_da_avaliacao(referencia):
    """Ajusta o config durante a rodada e devolve os valores originais no final."""
    chave_paga = os.getenv("GEMINI_API_KEY_AVALIACAO")
    novos = {
        "DATA_REFERENCIA": date.fromisoformat(referencia),
        "COTA_ORIGEM": cota.AVALIACAO,
        "GEMINI_MODEL": os.getenv("AVALIACAO_MODELO") or MODELO_PADRAO,
    }
    if chave_paga:
        novos.update(GEMINI_API_KEY=chave_paga, COTA_NIVEL="pago",
                     COTA_GEMINI_ARQUIVO=config.COTA_GEMINI_ARQUIVO.with_name("cota_gemini_pago.json"))
    antigos = {nome: getattr(config, nome) for nome in novos}
    for nome, valor in novos.items():
        setattr(config, nome, valor)
    if hasattr(gemini.cliente, "cache_clear"):
        gemini.cliente.cache_clear()
    try:
        yield
    finally:
        for nome, valor in antigos.items():
            setattr(config, nome, valor)
        if hasattr(gemini.cliente, "cache_clear"):
            gemini.cliente.cache_clear()


@contextmanager
def api_no_banco(engine):
    sessao = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def get_db():
        db = sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = get_db
    try:
        yield TestClient(app), sessao
    finally:
        app.dependency_overrides.pop(database.get_db, None)


def criar_diario(sessao, diario):
    with sessao() as db:
        obra = db.query(models.Obra).filter(models.Obra.nome == diario["obra"]).one()
        novo = models.DiarioDeObra(
            data=date.fromisoformat(diario["data"]), clima_manha=diario["clima_manha"],
            clima_tarde=diario["clima_tarde"], observacoes_gerais=diario["observacao"],
            local_dia=diario["local"], obra_id=obra.id)
        novo.efetivos = [models.Efetivo(funcao=e["funcao"], quantidade=e["quantidade"], horas_trabalhadas=e["horas"])
                         for e in diario["efetivo"]]
        novo.equipamentos = [models.Equipamento(nome_item=q["nome"], tipo=q["tipo"], quantidade=q["quantidade"])
                             for q in diario["equipamentos"]]
        novo.gastos = [models.Gasto(item=g["item"], categoria=g["categoria"], valor=g["valor"]) for g in diario["gastos"]]
        db.add(novo)
        db.commit()


def numeros_no_texto(texto):
    return [float(n.replace(".", "").replace(",", ".")) for n in NUMERO.findall(texto or "")]


def conferir_valores(pergunta, texto):
    """Para cada número do gabarito, diz se aparece na resposta com até 1% de diferença."""
    encontrados = numeros_no_texto(texto)
    return {nome: any(abs(n - valor) <= max(abs(valor) * 0.01, 0.005) for n in encontrados)
            for nome, valor in pergunta.get("valores", {}).items()}


def perguntar(cliente, pergunta, obra_ids, esperar):
    corpo_requisicao = {"mensagem": pergunta["pergunta"], "historico": pergunta.get("turnos_anteriores", []),
                        "obra_id": obra_ids.get(pergunta["modo"])}
    tentativas = 0
    erros = []
    while True:
        tentativas += 1
        inicio = time.perf_counter()
        resposta = cliente.post("/ia/chat", json=corpo_requisicao)
        latencia = round(time.perf_counter() - inicio, 2)
        corpo = resposta.json() if resposta.headers.get("content-type", "").startswith("application/json") else {}
        texto = corpo.get("resposta", "") if isinstance(corpo, dict) else ""
        if any(sinal in texto for sinal in SINAIS_DE_COTA_ESGOTADA):
            raise ParadaPorCota(texto)
        # O ia.py do baseline devolve os erros do Gemini com HTTP 200 e "Erro técnico"; o novo usa 429 e 5xx.
        temporario = (texto.startswith("Erro técnico") and any(c in texto for c in ERROS_TEMPORARIOS)) \
            or resposta.status_code == 429 or resposta.status_code >= 500
        if temporario and tentativas <= len(ESPERAS_APOS_ERRO):
            erros.append({"http": resposta.status_code, "mensagem": texto[:200]})
            esperar(ESPERAS_APOS_ERRO[tentativas - 1])
            continue
        if resposta.status_code != 200 or texto.startswith("Erro técnico"):
            status = "erro"
        else:
            status = "ok"
        return {"status": status, "http": resposta.status_code, "tentativas": tentativas, "erros_das_tentativas": erros,
                "latencia_s": latencia,
                "resposta": corpo, "uso": corpo.get("uso") if isinstance(corpo, dict) else None,
                "valores_encontrados": conferir_valores(pergunta, texto)}


def ja_respondidas(saida):
    if not saida.is_file():
        return set()
    linhas = (json.loads(l) for l in saida.read_text(encoding="utf-8").splitlines() if l.strip())
    return {l["id"] for l in linhas if l["status"] == "ok"}


def rodar(rotulo, pasta_saida, ids=None, esperar=time.sleep):
    conjunto = json.loads(PERGUNTAS.read_text(encoding="utf-8"))
    banco = caminho_do_banco()
    saida = Path(pasta_saida) / f"{rotulo}.jsonl"
    saida.parent.mkdir(parents=True, exist_ok=True)
    feitas = ja_respondidas(saida)
    pendentes = [p for p in conjunto["perguntas"] if p["id"] not in feitas and (not ids or p["id"] in ids)]
    print(f"Rodada '{rotulo}': {len(feitas)} já respondidas, {len(pendentes)} pendentes. Banco: {banco}")
    if not pendentes:
        return 0

    engine = create_engine(f"sqlite:///{banco}")
    respondidas = 0
    try:
        with configuracao_da_avaliacao(conjunto["referencia"]), api_no_banco(engine) as (cliente, sessao):
            carregar_banco(engine)
            with sessao() as db:
                obra_ids = {o.nome: o.id for o in db.query(models.Obra)}
            fixos = {
                "rotulo": rotulo, "modelo": config.GEMINI_MODEL, "sdk": __import__("google.genai").genai.__version__,
                "nivel_cota": config.COTA_NIVEL, "commit": commit_atual(), "data_referencia": conjunto["referencia"],
                "hash_dados": hash_canonico(*(RAIZ / "dados" / a for a in ARQUIVOS_DE_DADOS)),
                "hash_perguntas": hash_canonico(PERGUNTAS),
                "hash_avaliador": hash_canonico(Path(__file__), RAIZ / "routers" / "ia.py"),
            }
            for indice, pergunta in enumerate(pendentes):
                if "preparacao" in pergunta:
                    criar_diario(sessao, pergunta["preparacao"]["criar_diario"])
                try:
                    resultado = perguntar(cliente, pergunta, obra_ids, esperar)
                finally:
                    if "preparacao" in pergunta:
                        carregar_banco(engine)  # desfaz o diário criado
                linha = {"id": pergunta["id"], "grupo": pergunta["grupo"], "modo": pergunta["modo"],
                         "reservada": pergunta["reservada"], "pergunta": pergunta["pergunta"],
                         "quando": datetime.now().isoformat(timespec="seconds"), **fixos, **resultado}
                with open(saida, "a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(linha, ensure_ascii=False) + "\n")
                respondidas += 1
                tokens = (resultado["uso"] or {}).get("tokens_total") or 0
                print(f"  {pergunta['id']}: {resultado['status']} ({resultado['tentativas']} tentativa(s), "
                      f"{tokens} tokens, {resultado['latencia_s']} s)")
                if indice < len(pendentes) - 1:
                    esperar(cota.espera_recomendada(tokens))
    except ParadaPorCota as e:
        print(f"Parado pela cota: {e}\nRode de novo depois que a cota voltar; o script continua de onde parou.")
    finally:
        engine.dispose()
    print(f"{respondidas} pergunta(s) gravada(s) em {saida}")
    return respondidas


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Roda o conjunto de avaliação do Analista IA.")
    parser.add_argument("--rotulo", required=True, help="nome da rodada, ex.: antes ou depois")
    parser.add_argument("--saida", default=str(RAIZ / "avaliacao" / "resultados"), help="pasta dos arquivos .jsonl")
    parser.add_argument("--ids", nargs="*", help="só estas perguntas (ex.: Q1 Q2)")
    args = parser.parse_args(argumentos)
    rodar(args.rotulo, args.saida, set(args.ids or []))


if __name__ == "__main__":
    main()

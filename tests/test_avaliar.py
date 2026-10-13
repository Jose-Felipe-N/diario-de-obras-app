"""Script de avaliação, rodado com um Gemini falso: nenhuma chamada real e nenhuma cota gasta."""

import json
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from google.genai import errors

import config
import gemini
import models
from avaliacao import avaliar


class GeminiFalso:
    def __init__(self, falhas_iniciais=0):
        self.prompts = []
        self.falhas_iniciais = falhas_iniciais
        self.models = SimpleNamespace(generate_content=self._gerar)

    def _gerar(self, model, contents, config=None):
        self.prompts.append(getattr(config, "system_instruction", None) or "")
        if self.falhas_iniciais:
            self.falhas_iniciais -= 1
            raise errors.APIError(503, {"error": {"code": 503, "message": "modelo sobrecarregado"}})
        uso = SimpleNamespace(prompt_token_count=100, candidates_token_count=10,
                              thoughts_token_count=5, total_token_count=115)
        return SimpleNamespace(function_calls=None, candidates=[],
                               text=json.dumps({"resposta": "R$ 10.841,50", "gerar_grafico": False}),
                               usage_metadata=uso)


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARIO_DB_PATH", str(tmp_path / "eval.db"))
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("AVALIACAO_MODELO", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_AVALIACAO", raising=False)
    falso = GeminiFalso()
    monkeypatch.setattr(gemini, "cliente", lambda: falso)
    return SimpleNamespace(pasta=tmp_path, falso=falso, banco=tmp_path / "eval.db")


def linhas(pasta, rotulo="teste"):
    return [json.loads(l) for l in (pasta / f"{rotulo}.jsonl").read_text(encoding="utf-8").splitlines()]


def sem_espera(_):
    pass


def test_recusa_sem_banco_definido(monkeypatch, tmp_path):
    monkeypatch.delenv("DIARIO_DB_PATH", raising=False)
    with pytest.raises(SystemExit):
        avaliar.rodar("teste", tmp_path, esperar=sem_espera)


def test_recusa_o_banco_de_desenvolvimento(monkeypatch, tmp_path):
    monkeypatch.setenv("DIARIO_DB_PATH", "diario_obra.db")
    with pytest.raises(SystemExit, match="desenvolvimento"):
        avaliar.rodar("teste", tmp_path, esperar=sem_espera)


def test_rodada_completa(ambiente, monkeypatch):
    monkeypatch.setattr(config, "COTA_NIVEL", "pago")
    assert avaliar.rodar("teste", ambiente.pasta, esperar=sem_espera) == 20

    resultado = linhas(ambiente.pasta)
    assert [l["id"] for l in resultado] == [f"Q{i}" for i in range(1, 21)]
    assert all(l["status"] == "ok" and l["uso"]["tokens_total"] == 115 for l in resultado)
    assert {l["modelo"] for l in resultado} == {"gemini-3.8-flash"}
    assert all(l["hash_dados"] and l["hash_perguntas"] and l["hash_avaliador"] for l in resultado)
    q11 = next(l for l in resultado if l["id"] == "Q11")
    assert q11["valores_encontrados"] == {"cimento": True, "compras_de_cimento": False}

    assert all("Hoje é 08/10/2026" in p for p in ambiente.falso.prompts)
    assert config.DATA_REFERENCIA is None and config.COTA_ORIGEM == "desenvolvimento"


def test_modelo_do_app_no_env_nao_muda_o_modelo_da_avaliacao(ambiente, monkeypatch):
    monkeypatch.setattr(config, "COTA_NIVEL", "pago")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")  # como se viesse do .env do app
    avaliar.rodar("teste", ambiente.pasta, ids=["Q16"], esperar=sem_espera)
    monkeypatch.setenv("AVALIACAO_MODELO", "gemini-3.7-flash")    # troca de propósito
    avaliar.rodar("outro", ambiente.pasta, ids=["Q16"], esperar=sem_espera)
    assert [l["modelo"] for l in linhas(ambiente.pasta)] == ["gemini-3.8-flash"]
    assert [l["modelo"] for l in linhas(ambiente.pasta, "outro")] == ["gemini-3.7-flash"]


def test_diario_da_q20_existe_durante_a_pergunta_e_some_depois(ambiente, monkeypatch):
    monkeypatch.setattr(config, "COTA_NIVEL", "pago")
    engine = create_engine(f"sqlite:///{ambiente.banco}")

    def diarios_de_hoje():
        with sessionmaker(bind=engine)() as db:
            return db.query(models.DiarioDeObra).filter(models.DiarioDeObra.data == date(2026, 10, 8)).count()

    durante = []
    perguntar_original = avaliar.perguntar

    def espiar(*args, **kwargs):
        durante.append(diarios_de_hoje())
        return perguntar_original(*args, **kwargs)

    monkeypatch.setattr(avaliar, "perguntar", espiar)
    avaliar.rodar("teste", ambiente.pasta, ids={"Q20"}, esperar=sem_espera)
    assert durante == [1]
    with sessionmaker(bind=engine)() as db:
        assert db.query(models.DiarioDeObra).filter(models.DiarioDeObra.data == date(2026, 10, 8)).count() == 0
        assert db.query(models.DiarioDeObra).count() == 189
    engine.dispose()


def test_para_na_cota_da_avaliacao_e_retoma_de_onde_parou(ambiente):
    assert avaliar.rodar("teste", ambiente.pasta, esperar=sem_espera) == 18
    assert len(linhas(ambiente.pasta)) == 18
    assert avaliar.rodar("teste", ambiente.pasta, esperar=sem_espera) == 0
    assert len(ambiente.falso.prompts) == 18


def test_tenta_de_novo_depois_de_erro_temporario(ambiente, monkeypatch):
    monkeypatch.setattr(config, "COTA_NIVEL", "pago")
    ambiente.falso.falhas_iniciais = 1
    avaliar.rodar("teste", ambiente.pasta, ids={"Q1"}, esperar=sem_espera)
    (linha,) = linhas(ambiente.pasta)
    assert linha["status"] == "ok" and linha["tentativas"] == 2

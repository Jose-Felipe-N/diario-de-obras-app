"""Contador de cota do Gemini: limites, dias reservados, fuso do Pacífico, ajustes e escrita concorrente.

Nenhum teste chama a API do Gemini.
"""

import json
import subprocess
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

import config
import cota
import gemini
from cota import AVALIACAO, DESENVOLVIMENTO, EXTERNO, FUSO_DA_COTA, FUSO_LOCAL, Contador, CotaEsgotada

MODELO = "gemini-3.8-flash"
DIA = "2026-10-12"
AGORA = datetime(2026, 10, 12, 10, 0, tzinfo=FUSO_DA_COTA)


@pytest.fixture
def contador(tmp_path):
    return Contador(tmp_path / "cota.json")


def usar(contador, vezes, origem=DESENVOLVIMENTO, modelo=MODELO):
    for _ in range(vezes):
        contador.registrar(modelo, origem, agora=AGORA)


def uso(contador, modelo=MODELO):
    s = contador.situacao(DIA)[modelo]
    return s[AVALIACAO], s[DESENVOLVIMENTO], s[EXTERNO]


def test_dia_comum_libera_as_20_e_nao_anota_a_recusa(contador):
    usar(contador, 20)
    with pytest.raises(CotaEsgotada, match="20 de 20"):
        contador.registrar(MODELO, agora=AGORA)
    assert uso(contador) == (0, 20, 0)


def test_dia_reservado_guarda_18_para_a_avaliacao(contador):
    contador.reservar(DIA)
    usar(contador, 2)
    with pytest.raises(CotaEsgotada, match="dia de medição"):
        contador.registrar(MODELO, agora=AGORA)
    usar(contador, 18, AVALIACAO)
    with pytest.raises(CotaEsgotada):
        contador.registrar(MODELO, AVALIACAO, agora=AGORA)
    assert uso(contador) == (18, 2, 0)


def test_avaliacao_nunca_passa_de_18(contador):
    usar(contador, 18, AVALIACAO)
    with pytest.raises(CotaEsgotada, match="18 chamadas"):
        contador.registrar(MODELO, AVALIACAO, agora=AGORA)
    usar(contador, 2)
    with pytest.raises(CotaEsgotada, match="20 de 20"):
        contador.registrar(MODELO, agora=AGORA)


def test_liberar_desfaz_a_reserva(contador):
    contador.reservar(DIA)
    contador.liberar(DIA)
    usar(contador, 20)
    assert uso(contador) == (0, 20, 0)


def test_modelos_tem_contas_separadas(contador):
    usar(contador, 20, modelo="gemini-2.5-flash")
    with pytest.raises(CotaEsgotada):
        contador.registrar("gemini-2.5-flash", agora=AGORA)
    usar(contador, 1)
    usar(contador, 30, modelo="gemini-embedding-2")
    assert uso(contador) == (0, 1, 0)


def test_ajuste_faz_o_total_bater_com_o_painel(contador):
    usar(contador, 5)
    contador.ajustar(DIA, MODELO, 8, "testes no Playground")
    assert uso(contador) == (0, 5, 3)
    usar(contador, 12)
    with pytest.raises(CotaEsgotada, match="20 de 20"):
        contador.registrar(MODELO, agora=AGORA)
    ajuste = json.loads(contador.arquivo.read_text(encoding="utf-8"))["ajustes"][0]
    assert (ajuste["contador"], ajuste["painel"], ajuste["motivo"]) == (5, 8, "testes no Playground")


def test_dia_da_cota_segue_o_horario_do_pacifico():
    # 03h de 12/10 em Brasília ainda é 23h de 11/10 em Los Angeles.
    assert cota.dia_da_cota(datetime(2026, 10, 12, 3, 0, tzinfo=FUSO_LOCAL)) == "2026-10-11"
    assert cota.dia_da_cota(datetime(2026, 10, 12, 5, 0, tzinfo=FUSO_LOCAL)) == "2026-10-12"


def test_renovacao_no_horario_de_brasilia():
    assert cota.proxima_renovacao(AGORA) == "04h"  # outubro: horário de verão nos EUA
    assert cota.proxima_renovacao(datetime(2026, 12, 1, 10, 0, tzinfo=FUSO_DA_COTA)) == "05h"


def test_espera_recomendada():
    assert cota.espera_recomendada(500) == 12
    assert cota.espera_recomendada(100_000) == 24


def test_escritas_simultaneas_nao_perdem_contagem(tmp_path):
    arquivo = tmp_path / "cota.json"
    codigo = (f"from cota import Contador\nc = Contador(r'{arquivo}')\n"
              "for _ in range(25): c.registrar('gemini-embedding-2')")
    processos = [subprocess.Popen([sys.executable, "-c", codigo], cwd=config.RAIZ) for _ in range(4)]
    assert all(p.wait(timeout=120) == 0 for p in processos)
    dias = json.loads(arquivo.read_text(encoding="utf-8"))["dias"].values()
    assert sum(d["gemini-embedding-2"][DESENVOLVIMENTO] for d in dias) == 100


def test_comandos_do_terminal(capsys):
    cota.main(["reservar", DIA])
    cota.main(["situacao", DIA])
    assert "DIA RESERVADO" in capsys.readouterr().out
    assert cota.Contador().situacao(DIA)[MODELO]["reservado"]


class ClienteFalso:
    def __init__(self):
        self.chamadas = []
        self.models = SimpleNamespace(generate_content=self._gerar)

    def _gerar(self, **kwargs):
        self.chamadas.append(kwargs)
        return SimpleNamespace(function_calls=None, candidates=[], usage_metadata=None,
                               text=json.dumps({"resposta": "ok", "gerar_grafico": False}))


def test_gerar_anota_antes_e_nao_chama_a_api_sem_cota(monkeypatch, contador):
    falso = ClienteFalso()
    monkeypatch.setattr(gemini, "cliente", lambda: falso)
    gemini.gerar(MODELO, "oi", contador=contador)
    assert len(falso.chamadas) == 1 and contador.situacao()[MODELO][DESENVOLVIMENTO] == 1
    for _ in range(19):
        gemini.gerar(MODELO, "oi", contador=contador)
    with pytest.raises(CotaEsgotada):
        gemini.gerar(MODELO, "oi", contador=contador)
    assert len(falso.chamadas) == 20


def test_chat_do_app_respeita_a_cota(cliente, monkeypatch):
    falso = ClienteFalso()
    monkeypatch.setattr(gemini, "cliente", lambda: falso)
    pergunta = {"mensagem": "como está a obra?", "historico": []}
    assert cliente.post("/ia/chat", json=pergunta).json()["resposta"] == "ok"

    usar_ate_o_fim = Contador()
    for _ in range(19):
        usar_ate_o_fim.registrar(config.GEMINI_MODEL)
    resposta = cliente.post("/ia/chat", json=pergunta).json()["resposta"]
    assert resposta.startswith("Limite diário do assistente atingido")
    assert len(falso.chamadas) == 1


def test_embeddings_contam_cada_texto(contador):
    contador.registrar("gemini-embedding-2", agora=AGORA, quantidade=45)
    contador.registrar("gemini-embedding-2", agora=AGORA, quantidade=45)
    assert contador.situacao(DIA)["gemini-embedding-2"][DESENVOLVIMENTO] == 90
    with pytest.raises(CotaEsgotada):
        contador.registrar("gemini-embedding-2", agora=AGORA, quantidade=911)

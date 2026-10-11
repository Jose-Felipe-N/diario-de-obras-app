"""Analista IA com ferramentas: SQL das ferramentas, escopo da obra e laço de function calling.

O banco é o de avaliação, carregado em memória; o Gemini é um roteiro falso.
"""

import json
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google.genai import errors, types
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import config
import database
import gemini
import models
from analista import agente
from analista.ferramentas import Ferramentas, executar
from avaliacao.carga import carregar_banco
from main import app

USO = SimpleNamespace(prompt_token_count=50, candidates_token_count=5, thoughts_token_count=3, total_token_count=58)


@pytest.fixture(scope="module")
def sessao():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    carregar_banco(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def hoje_da_avaliacao(monkeypatch):
    monkeypatch.setattr(config, "DATA_REFERENCIA", date(2026, 10, 8))


@pytest.fixture
def db(sessao):
    with sessao() as s:
        yield s


def id_da_obra(db, nome):
    return db.query(models.Obra).filter(models.Obra.nome == nome).one().id


# ── ferramentas (SQL), sem modelo ─────────────────────────────────────────────

def test_gastos_de_um_item(db):
    r = Ferramentas(db, id_da_obra(db, "Casa Condomínio")).gastos(item="Cimento")
    assert r["total"] == 10841.5 and r["lancamentos"] == 19


def test_gastos_distingue_zero_de_sem_registro(db):
    casa = Ferramentas(db, id_da_obra(db, "Casa Condomínio"))
    zero = casa.gastos(categoria="Mão de Obra Externa")
    assert zero["total"] == 0 and "gasto foi zero" in zero["aviso"]
    sem_registro = casa.gastos(inicio="2026-10-07", fim="2026-10-07")
    assert "falta de registro" in sem_registro["aviso"]


def test_gastos_na_visao_geral_somam_todas_as_obras(db):
    r = Ferramentas(db).gastos(categoria="Material de Construção", inicio="2026-09-28", fim="2026-10-04")
    assert r["por_obra"] == {"Casa Condomínio": 6563.85, "Galpão Logístico": 71445.07}


def test_diarios_mostram_dia_sem_registro_e_dia_parado(db):
    casa = Ferramentas(db, id_da_obra(db, "Casa Condomínio"))
    assert casa.diarios("2026-10-07", "2026-10-07")["datas_sem_diario"] == ["2026-10-07"]
    (parado,) = casa.diarios("2026-09-12", "2026-09-12")["diarios"]
    assert parado["dia_parado"] and parado["pessoas"] == 0 and parado["clima"] == {"manha": "Tempestade", "tarde": "Tempestade"}


def test_diarios_limitam_o_periodo(db):
    r = executar(Ferramentas(db, id_da_obra(db, "Casa Condomínio")), "diarios", {"inicio": "2026-08-01", "fim": "2026-10-07"})
    assert "31 dias" in r["erro"]


def test_cronograma_calcula_o_atraso_com_a_data_de_referencia(db):
    etapas = {e["etapa"]: e for e in Ferramentas(db).cronograma("Galpão")["etapas"]}
    estrutura = etapas["2. Estrutura Metálica"]
    assert (estrutura["dias_decorridos"], estrutura["situacao"]) == (85, "atrasada")


def test_orcamento_ligado_a_obra(db):
    galpao = Ferramentas(db).orcamento("Galpão Logístico")
    assert galpao["percentual_do_material_orcado"] == 115.0
    casa = Ferramentas(db).orcamento("Casa Condomínio")
    assert casa["orcamentos"][0]["projeto"] == "Residência Lote 12" and casa["percentual_do_material_orcado"] == 70.0


def test_obra_selecionada_bloqueia_outra_obra(db):
    casa = Ferramentas(db, id_da_obra(db, "Casa Condomínio"))
    r = executar(casa, "gastos", {"obra": "Galpão Logístico"})
    assert "restrita" in r["erro"] and "total" not in r
    assert [o["obra"] for o in casa.listar_obras()["obras"]] == ["Casa Condomínio"]


def test_observacoes_trazem_so_dias_com_texto(db):
    textos = Ferramentas(db, id_da_obra(db, "Casa Condomínio")).observacoes()["observacoes"]
    assert textos and all(t["texto"].strip() for t in textos)
    assert any("concessionária" in t["texto"].lower() for t in textos)


# ── laço do agente, com um Gemini roteirizado ─────────────────────────────────

def chamar(nome, **argumentos):
    chamada = types.FunctionCall(name=nome, args=argumentos)
    conteudo = types.Content(role="model", parts=[types.Part(function_call=chamada)])
    return SimpleNamespace(function_calls=[chamada], candidates=[SimpleNamespace(content=conteudo)], text=None,
                           usage_metadata=USO)


def responder(**campos):
    texto = json.dumps({"gerar_grafico": False, **campos})
    conteudo = types.Content(role="model", parts=[types.Part(text=texto)])
    return SimpleNamespace(function_calls=None, candidates=[SimpleNamespace(content=conteudo)], text=texto,
                           usage_metadata=USO)


class Roteiro:
    def __init__(self, *passos):
        self.passos = list(passos)
        self.chamadas = []
        self.models = SimpleNamespace(generate_content=self._gerar)

    def _gerar(self, model, contents, config=None):
        self.chamadas.append({"contents": list(contents), "config": config})
        passo = self.passos.pop(0)
        if isinstance(passo, Exception):
            raise passo
        return passo


@pytest.fixture
def api(sessao, monkeypatch):
    monkeypatch.setattr(config, "COTA_NIVEL", "pago")

    def get_db():
        db = sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def usar_roteiro(monkeypatch, *passos):
    roteiro = Roteiro(*passos)
    monkeypatch.setattr(gemini, "cliente", lambda: roteiro)
    return roteiro


def perguntar(api, sessao, mensagem, obra=None, historico=()):
    with sessao() as db:
        obra_id = id_da_obra(db, obra) if obra else None
    return api.post("/ia/chat", json={"mensagem": mensagem, "historico": list(historico), "obra_id": obra_id})


def test_modelo_pede_ferramenta_e_responde(api, sessao, monkeypatch):
    roteiro = usar_roteiro(monkeypatch, chamar("gastos", item="Cimento"), responder(resposta="R$ 10.841,50 em cimento."))
    r = perguntar(api, sessao, "quanto já foi de cimento?", "Casa Condomínio")
    assert r.status_code == 200 and r.json()["resposta"] == "R$ 10.841,50 em cimento."
    uso = r.json()["uso"]
    assert uso["chamadas"] == 2 and uso["tokens_total"] == 116 and uso["ferramentas"][0]["nome"] == "gastos"
    devolvido = roteiro.chamadas[1]["contents"][-1].parts[0].function_response.response
    assert devolvido["total"] == 10841.5


def test_instrucoes_trazem_a_data_e_o_escopo(api, sessao, monkeypatch):
    roteiro = usar_roteiro(monkeypatch, responder(resposta="ok"))
    perguntar(api, sessao, "oi", "Galpão Logístico")
    instrucao = roteiro.chamadas[0]["config"].system_instruction
    assert "Hoje é 08/10/2026 (quinta)" in instrucao and "Semana passada: 2026-09-28 a 2026-10-04" in instrucao
    assert "restrita à obra 'Galpão Logístico'" in instrucao and "Casa Condomínio" not in instrucao
    assert roteiro.chamadas[0]["config"].automatic_function_calling.disable


def test_historico_vira_turnos_do_modelo(api, sessao, monkeypatch):
    roteiro = usar_roteiro(monkeypatch, responder(resposta="R$ 71.445,07"))
    historico = [{"role": "user", "content": "material na casa semana passada?"},
                 {"role": "assistant", "content": "R$ 6.563,85."}]
    perguntar(api, sessao, "e no galpão?", historico=historico)
    papeis = [c.role for c in roteiro.chamadas[0]["contents"]]
    assert papeis == ["user", "model", "user"]


def test_historico_malformado_e_recusado(api, sessao):
    r = api.post("/ia/chat", json={"mensagem": "oi", "historico": [{"quem": "eu"}]})
    assert r.status_code == 422


def test_grafico_vira_dicionario_para_a_tela(api, sessao, monkeypatch):
    usar_roteiro(monkeypatch, responder(resposta="ok", gerar_grafico=True, tipo_grafico="barras", titulo_grafico="T",
                                        dados_grafico=[{"rotulo": "Cimento", "valor": 10.5}]))
    corpo = perguntar(api, sessao, "gráfico", "Casa Condomínio").json()
    assert corpo["gerar_grafico"] and corpo["dados_grafico"] == {"Cimento": 10.5}


def test_ultima_volta_proibe_novas_ferramentas(api, sessao, monkeypatch):
    passos = [chamar("listar_obras") for _ in range(agente.MAX_CHAMADAS - 1)] + [responder(resposta="ok")]
    roteiro = usar_roteiro(monkeypatch, *passos)
    assert perguntar(api, sessao, "?", "Casa Condomínio").json()["uso"]["chamadas"] == agente.MAX_CHAMADAS
    ultima = roteiro.chamadas[-1]["config"].tool_config.function_calling_config.mode
    assert ultima == types.FunctionCallingConfigMode.NONE


def test_resposta_fora_do_schema_vira_mensagem_amigavel(api, sessao, monkeypatch):
    texto_ruim = SimpleNamespace(function_calls=None, candidates=[], text="isto não é json", usage_metadata=USO)
    usar_roteiro(monkeypatch, texto_ruim)
    r = perguntar(api, sessao, "?", "Casa Condomínio")
    assert r.status_code == 502 and "não é json" not in r.json()["resposta"]


@pytest.mark.parametrize("codigo, status, trecho", [(503, 503, "sobrecarregado"), (429, 429, "Espere um minuto")])
def test_erros_da_api_viram_status_e_mensagem(api, sessao, monkeypatch, codigo, status, trecho):
    usar_roteiro(monkeypatch, errors.APIError(codigo, {"error": {"code": codigo, "message": "segredo interno"}}))
    r = perguntar(api, sessao, "?", "Casa Condomínio")
    assert r.status_code == status and trecho in r.json()["resposta"] and "segredo" not in r.json()["resposta"]


def test_erro_inesperado_nao_expoe_detalhes(api, sessao, monkeypatch):
    usar_roteiro(monkeypatch, RuntimeError("senha=123"))
    r = perguntar(api, sessao, "?", "Casa Condomínio")
    assert r.status_code == 500 and "senha" not in r.json()["resposta"]

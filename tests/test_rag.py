"""RAG das observações: indexação, filtros por obra e data, reconciliação com o banco e falhas de embedding.

Usa um embedder falso (palavras em comum geram vetores próximos); nenhuma chamada ao Gemini.
"""

import hashlib
import math
import re
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from analista.ferramentas import Ferramentas
from analista.rag import Indice
from avaliacao.carga import carregar_banco

TOTAL_DE_OBSERVACOES = 142  # 124 de rotina + 18 eventos


class EmbedderFalso:
    def __init__(self):
        self.textos = 0
        self.falhar = False

    def __call__(self, textos):
        if self.falhar:
            raise RuntimeError("503 UNAVAILABLE")
        self.textos += len(textos)
        return [self.vetor(t) for t in textos]

    @staticmethod
    def vetor(texto):
        v = [0.0] * 1024
        for palavra in re.findall(r"\w{4,}", texto.lower()):
            v[int(hashlib.md5(palavra.encode()).hexdigest(), 16) % 1024] += 1
        norma = math.sqrt(sum(x * x for x in v)) or 1
        return [x / norma for x in v]


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    carregar_banco(engine)
    with sessionmaker(bind=engine)() as sessao:
        yield sessao


@pytest.fixture
def embedder():
    return EmbedderFalso()


@pytest.fixture
def indice(db, embedder, tmp_path):
    return Indice(db, embutir=embedder, pasta=tmp_path / "chroma", esperar=lambda s: None)


def obra(db, nome):
    return db.query(models.Obra).filter(models.Obra.nome == nome).one()


def test_indexa_todas_as_observacoes_uma_vez(indice, embedder):
    assert indice.reconciliar() == []
    assert indice.colecao.count() == TOTAL_DE_OBSERVACOES and embedder.textos == TOTAL_DE_OBSERVACOES
    indice.reconciliar()
    assert embedder.textos == TOTAL_DE_OBSERVACOES  # nada novo para indexar


def test_busca_respeita_obra_e_periodo(db, indice):
    casa = obra(db, "Casa Condomínio")
    resultados, _ = indice.buscar("cano da rua vala concessionária", [casa.id])
    assert resultados[0]["data"] == "2026-08-27" and "concessionária" in resultados[0]["texto"].lower()
    assert {r["obra"] for r in resultados} == {"Casa Condomínio"}
    no_periodo, _ = indice.buscar("parede", [casa.id], date(2026, 9, 20), date(2026, 9, 30))
    assert no_periodo and all("2026-09-20" <= r["data"] <= "2026-09-30" for r in no_periodo)


def test_edicao_e_exclusao_de_diario_entram_no_indice(db, indice, embedder):
    indice.reconciliar()
    casa = obra(db, "Casa Condomínio")
    editado = db.query(models.DiarioDeObra).filter(models.DiarioDeObra.obra_id == casa.id,
                                                   models.DiarioDeObra.data == date(2026, 9, 9)).one()
    editado.observacoes_gerais = "Guindaste emprestado chegou para içar as vigas da varanda."
    apagado = db.query(models.DiarioDeObra).filter(models.DiarioDeObra.obra_id == casa.id,
                                                   models.DiarioDeObra.data == date(2026, 9, 10)).one()
    db.delete(apagado)
    db.commit()
    antes = embedder.textos
    resultados, _ = indice.buscar("guindaste emprestado varanda", [casa.id])
    assert embedder.textos == antes + 2  # o diário editado e a consulta
    assert resultados[0]["data"] == "2026-09-09"
    assert indice.colecao.count() == TOTAL_DE_OBSERVACOES - 1


def test_falha_de_embedding_vira_aviso_e_nao_resposta_vazia(db, embedder, tmp_path):
    embedder.falhar = True
    ferramentas = Ferramentas(db, obra(db, "Casa Condomínio").id, indice=Indice(db, embutir=embedder, pasta=tmp_path, esperar=lambda s: None))
    sem_indice = ferramentas.buscar_observacoes("água")  # nada indexado: avisa em vez de dizer "não há registro"
    assert sem_indice["resultados"] == [] and f"{TOTAL_DE_OBSERVACOES} diário(s)" in sem_indice["aviso"]
    embedder.falhar = False
    ferramentas.buscar_observacoes("água")  # indexa tudo
    db.add(models.DiarioDeObra(data=date(2026, 10, 8), obra_id=obra(db, "Casa Condomínio").id,
                               observacoes_gerais="Betoneira parou de girar."))
    db.commit()
    chamadas = {"n": 0}

    def falha_so_na_indexacao(textos):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("503 UNAVAILABLE")
        return embedder(textos)

    ferramentas._indice.embutir = falha_so_na_indexacao
    r = ferramentas.buscar_observacoes("betoneira")
    assert "2026-10-08" in r["aviso"] and "Não conclua que não há registro" in r["aviso"]


def test_ferramenta_com_obra_selecionada_nao_mostra_outra_obra(db, indice):
    ferramentas = Ferramentas(db, obra(db, "Casa Condomínio").id, indice=indice)
    r = ferramentas.buscar_observacoes("perfis guindaste solda")
    assert r["resultados"] and {x["obra"] for x in r["resultados"]} == {"Casa Condomínio"}


def test_visao_geral_busca_em_todas_as_obras(db, indice):
    r = Ferramentas(db, indice=indice).buscar_observacoes("cliente pediu mudança janela cor parede")
    assert {"Casa Condomínio", "Reforma Loja Shopping"} <= {x["obra"] for x in r["resultados"]}


def test_indexacao_respeita_o_limite_de_textos_por_minuto(db, embedder, tmp_path):
    relogio = {"agora": 0.0}
    esperas = []

    def esperar(segundos):
        esperas.append(segundos)
        relogio["agora"] += segundos

    indice = Indice(db, embutir=embedder, pasta=tmp_path, esperar=esperar, relogio=lambda: relogio["agora"])
    assert indice.reconciliar() == []
    # 142 textos em lotes de 45: depois de 90 no mesmo minuto, a indexação espera a janela abrir.
    assert len(esperas) == 1 and esperas[0] > 59


def test_busca_indisponivel_vira_orientacao_para_o_modelo(db, indice):
    ferramentas = Ferramentas(db, obra(db, "Casa Condomínio").id, indice=indice)
    indice.reconciliar()

    def limite_atingido(textos):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    indice.embutir = limite_atingido
    from analista.ferramentas import executar
    r = executar(ferramentas, "buscar_observacoes", {"consulta": "água"})
    assert "indisponível" in r["erro"] and "observacoes" in r["erro"]

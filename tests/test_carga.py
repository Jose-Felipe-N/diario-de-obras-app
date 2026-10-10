"""O carregador grava no banco exatamente os dados congelados, e o seed protege um banco que já tem dados.

Tudo roda em bancos temporários; o banco de desenvolvimento não é tocado.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import models
import seed
from avaliacao import validacao_dados as v
from avaliacao.carga import carregar_banco
from main import app


@pytest.fixture(scope="module")
def dados():
    return v.carregar()


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    carregar_banco(engine)
    return engine


def contar(engine, modelo):
    with engine.connect() as conexao:
        return conexao.execute(select(func.count()).select_from(modelo)).scalar_one()


def diario(engine, obra, data):
    with sessionmaker(bind=engine)() as db:
        return db.execute(select(models.DiarioDeObra).join(models.Obra)
                          .where(models.Obra.nome == obra, models.DiarioDeObra.data == data)).scalar_one()


def test_contagens_batem_com_o_json(engine, dados):
    diarios = dados.diarios
    assert contar(engine, models.Obra) == 3
    assert contar(engine, models.EtapaObra) == sum(len(o["etapas"]) for o in dados.esqueleto["obras"])
    assert contar(engine, models.DiarioDeObra) == len(diarios) == 189
    assert contar(engine, models.Efetivo) == sum(len(d["efetivo"]) for d in diarios)
    assert contar(engine, models.Equipamento) == sum(len(d["equipamentos"]) for d in diarios)
    assert contar(engine, models.Gasto) == sum(len(d["gastos"]) for d in diarios)
    assert contar(engine, models.orcamento) == 6


def test_gastos_por_obra_batem_com_o_json(engine, dados):
    with engine.connect() as conexao:
        no_banco = dict(conexao.execute(
            select(models.Obra.nome, func.sum(models.Gasto.valor))
            .join(models.DiarioDeObra, models.DiarioDeObra.obra_id == models.Obra.id)
            .join(models.Gasto, models.Gasto.diario_id == models.DiarioDeObra.id)
            .group_by(models.Obra.nome)).all())
    for obra in no_banco:
        no_json = sum(g["valor"] for d in dados.diarios if d["obra"] == obra for g in d["gastos"])
        assert no_banco[obra] == pytest.approx(no_json), obra


def test_observacoes_nos_lugares_certos(engine, dados):
    e01 = next(e for e in dados.eventos["eventos"] if e["codigo"] == "E01")
    assert diario(engine, "Casa Condomínio", date.fromisoformat(e01["data"])).observacoes_gerais == e01["texto"]
    assert diario(engine, "Galpão Logístico", date(2026, 6, 17)).observacoes_gerais == ""
    assert diario(engine, "Reforma Loja Shopping", date(2026, 8, 29)).observacoes_gerais.startswith("Retoques finais")
    with engine.connect() as conexao:
        vazios = conexao.execute(select(func.count()).select_from(models.DiarioDeObra)
                                 .where(models.DiarioDeObra.observacoes_gerais == "")).scalar_one()
    assert vazios == 47


def test_dia_parado_sem_efetivo(engine):
    with sessionmaker(bind=engine)() as db:
        parado = db.execute(select(models.DiarioDeObra).join(models.Obra).where(
            models.Obra.nome == "Galpão Logístico", models.DiarioDeObra.data == date(2026, 6, 17))).scalar_one()
        assert parado.efetivos == []


def test_api_le_os_dados_carregados(engine):
    """Os dados respeitam as validações da API (ambiente, local, status e lucro)."""
    sessao = sessionmaker(bind=engine)

    def get_db():
        db = sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = get_db
    try:
        cliente = TestClient(app)
        obras = cliente.get("/obras/")
        assert obras.status_code == 200
        assert {o["nome"] for o in obras.json()} == {"Casa Condomínio", "Reforma Loja Shopping", "Galpão Logístico"}
        orcamentos = cliente.get("/orcamentos/")
        assert orcamentos.status_code == 200 and len(orcamentos.json()) == 6
        casa = next(o for o in obras.json() if o["nome"] == "Casa Condomínio")
        assert cliente.get(f"/obras/{casa['id']}/progresso").json() == {"progresso": 20.0}
    finally:
        app.dependency_overrides.clear()


def banco_com_uma_obra(caminho):
    engine = create_engine(f"sqlite:///{caminho}")
    models.Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add(models.Obra(nome="Obra do usuário", ambiente="Aberto"))
        db.commit()
    return engine


def nao_pergunte(_):
    raise AssertionError("o seed não deveria perguntar")


def test_seed_pergunta_antes_de_apagar_um_banco_com_dados(tmp_path):
    engine = banco_com_uma_obra(tmp_path / "dev.db")
    assert seed.main([], engine=engine, perguntar=lambda _: "n") is False
    assert contar(engine, models.Obra) == 1
    assert seed.main([], engine=engine, perguntar=lambda _: "s") is True
    assert contar(engine, models.Obra) == 3
    engine.dispose()


def test_seed_com_sim_nao_pergunta(tmp_path):
    engine = banco_com_uma_obra(tmp_path / "dev.db")
    assert seed.main(["--sim"], engine=engine, perguntar=nao_pergunte) is True
    assert contar(engine, models.Obra) == 3
    engine.dispose()


def test_seed_em_banco_novo_nao_pergunta(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'novo.db'}")
    assert seed.main([], engine=engine, perguntar=nao_pergunte) is True
    assert contar(engine, models.Obra) == 3
    engine.dispose()

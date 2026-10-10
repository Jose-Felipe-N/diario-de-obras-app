"""Fixtures compartilhadas: um cliente da API ligado a um banco SQLite em memória."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import config
import database
import models
from main import app


@pytest.fixture(autouse=True)
def cota_isolada(tmp_path, monkeypatch):
    """Nenhum teste lê ou grava o contador de cota real."""
    monkeypatch.setattr(config, "COTA_GEMINI_ARQUIVO", tmp_path / "cota_gemini.json")


@pytest.fixture
def cliente():
    """Cada teste ganha um banco novo e vazio; o banco de desenvolvimento não é tocado."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    models.Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def get_db_teste():
        db = sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = get_db_teste
    yield TestClient(app)
    app.dependency_overrides.clear()

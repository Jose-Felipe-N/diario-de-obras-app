"""Fixtures compartilhadas: um cliente da API ligado a um banco SQLite em memória."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import models
from main import app


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

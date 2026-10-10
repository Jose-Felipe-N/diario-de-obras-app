"""Fixtures compartilhadas: um cliente da API ligado a um banco SQLite em memória."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import models
from main import app
from routers import dashboard, diarios, obras, registros


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

    # Enquanto o get_db não é único (item f da etapa 1), cada router tem a sua cópia.
    for dependencia in (database.get_db, obras.get_db, diarios.get_db, registros.get_db, dashboard.get_db):
        app.dependency_overrides[dependencia] = get_db_teste
    yield TestClient(app)
    app.dependency_overrides.clear()

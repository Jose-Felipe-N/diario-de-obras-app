from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config

SQLALCHEMY_DATABASE_URL = f"sqlite:///{config.DIARIO_DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Sessão do banco para uma requisição, fechada ao final. Usada por todos os routers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
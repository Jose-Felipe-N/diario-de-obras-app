from fastapi import FastAPI
import models
from database import engine
from routers import obras, diarios, registros, dashboard, orcamentos

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Diário de Obra")


@app.get("/")
def home():
    return {"mensagem": "API do Diário de Obra está rodando!"}


# Registro dos routers
app.include_router(obras.router)
app.include_router(diarios.router)
app.include_router(registros.router)
app.include_router(dashboard.router)
app.include_router(orcamentos.router)
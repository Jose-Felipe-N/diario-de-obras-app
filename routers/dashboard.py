from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import models
from database import SessionLocal

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def obter_dashboard(db: Session = Depends(get_db)):
    hoje = date.today()

    obras_ativas = db.query(models.Obra).filter(models.Obra.status == "Em andamento").count()
    obras_pausadas = db.query(models.Obra).filter(models.Obra.status == "Pausada").all()

    diarios_hoje = db.query(models.DiarioDeObra).filter(models.DiarioDeObra.data == hoje).all()
    ids_diarios_hoje = [d.id for d in diarios_hoje]

    efetivo_hoje = 0
    gastos_hoje = 0.0

    if ids_diarios_hoje:
        efetivo_hoje = db.query(func.sum(models.Efetivo.quantidade)).filter(
            models.Efetivo.diario_id.in_(ids_diarios_hoje)
        ).scalar() or 0
        gastos_hoje = db.query(func.sum(models.Gasto.valor)).filter(
            models.Gasto.diario_id.in_(ids_diarios_hoje)
        ).scalar() or 0.0

    alertas_clima = []
    diarios_preenchidos = []

    for diario in diarios_hoje:
        diarios_preenchidos.append({"obra": diario.obra.nome})
        if diario.clima_manha in ["Chuva", "Tempestade"] or diario.clima_tarde in ["Chuva", "Tempestade"]:
            alertas_clima.append({
                "obra": diario.obra.nome,
                "clima": f"Manhã: {diario.clima_manha}, Tarde: {diario.clima_tarde}"
            })

    return {
        "obras_ativas": obras_ativas,
        "efetivo_hoje": int(efetivo_hoje),
        "gastos_hoje": float(gastos_hoje),
        "alertas_pausadas": [{"obra": o.nome} for o in obras_pausadas],
        "alertas_clima": alertas_clima,
        "diarios_preenchidos": diarios_preenchidos
    }
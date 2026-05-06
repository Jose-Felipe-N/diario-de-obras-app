from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas
from database import SessionLocal

router = APIRouter(tags=["Efetivos, Gastos e Equipamentos"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Efetivos ───────────────────────────────────────────────────────────────────

@router.post("/efetivos/")
def criar_efetivo(efetivo_recebido: schemas.EfetivoCreate, db: Session = Depends(get_db)):
    novo_efetivo = models.Efetivo(
        funcao=efetivo_recebido.funcao,
        quantidade=efetivo_recebido.quantidade,
        horas_trabalhadas=efetivo_recebido.horas_trabalhadas,
        diario_id=efetivo_recebido.diario_id
    )
    db.add(novo_efetivo)
    db.commit()
    db.refresh(novo_efetivo)
    return novo_efetivo


@router.get("/efetivos/", response_model=list[schemas.EfetivoResponse])
def listar_efetivos(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.Efetivo).offset(skip).limit(limit).all()


# ── Gastos ─────────────────────────────────────────────────────────────────────

@router.post("/gastos/")
def criar_gasto(gasto: schemas.GastoCreate, db: Session = Depends(get_db)):
    novo_gasto = models.Gasto(**gasto.dict())
    db.add(novo_gasto)
    db.commit()
    db.refresh(novo_gasto)
    return novo_gasto


@router.get("/gastos/", response_model=list[schemas.GastoResponse])
def listar_gastos(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.Gasto).offset(skip).limit(limit).all()


# ── Equipamentos ───────────────────────────────────────────────────────────────

@router.post("/equipamentos/")
def criar_equipamento(equipamento_recebido: schemas.EquipamentoCreate, db: Session = Depends(get_db)):
    novo_equipamento = models.Equipamento(
        nome_item=equipamento_recebido.nome_item,
        tipo=equipamento_recebido.tipo,
        quantidade=equipamento_recebido.quantidade,
        diario_id=equipamento_recebido.diario_id
    )
    db.add(novo_equipamento)
    db.commit()
    db.refresh(novo_equipamento)
    return novo_equipamento


@router.get("/equipamentos/", response_model=list[schemas.EquipamentoResponse])
def listar_equipamentos(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.Equipamento).offset(skip).limit(limit).all()
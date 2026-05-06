from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from database import SessionLocal

router = APIRouter(prefix="/obras", tags=["Obras"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def criar_obra(obra_recebida: schemas.ObraCreate, db: Session = Depends(get_db)):
    nova_obra = models.Obra(
        nome=obra_recebida.nome,
        endereco=obra_recebida.endereco,
        data_inicio=obra_recebida.data_inicio,
        status=obra_recebida.status,
        ambiente=obra_recebida.ambiente
    )
    db.add(nova_obra)
    db.commit()
    db.refresh(nova_obra)
    return nova_obra


@router.get("/", response_model=list[schemas.ObraResponse])
def listar_obras(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.Obra).offset(skip).limit(limit).all()


@router.get("/{obra_id}", response_model=schemas.ObraResponse)
def obter_obra(obra_id: int, db: Session = Depends(get_db)):
    obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
    if obra is None:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    return obra


@router.delete("/{obra_id}")
def deletar_obra(obra_id: int, db: Session = Depends(get_db)):
    obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
    if obra is None:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    db.delete(obra)
    db.commit()
    return {"mensagem": f"A obra com ID {obra_id} foi removida com sucesso!"}


@router.put("/{obra_id}/status")
def atualizar_status_obra(obra_id: int, dados: schemas.StatusUpdate, db: Session = Depends(get_db)):
    obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    obra.status = dados.status
    db.commit()
    return {"mensagem": "Status atualizado com sucesso"}
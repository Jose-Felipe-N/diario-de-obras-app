from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from database import get_db

router = APIRouter(prefix="/obras", tags=["Obras"])


@router.post("/")
def criar_obra(obra: schemas.ObraCreate, db: Session = Depends(get_db)):
    nova_obra = models.Obra(
        nome=obra.nome,
        endereco=obra.endereco,
        data_inicio=obra.data_inicio,
        status=obra.status,
        ambiente=obra.ambiente
    )
    db.add(nova_obra)
    db.commit()
    db.refresh(nova_obra) 

    if obra.etapas:
        for etapa_in in obra.etapas:
            nova_etapa = models.EtapaObra(
                nome_etapa=etapa_in.nome_etapa,
                peso_percentual=etapa_in.peso_percentual,
                dias_estimados=etapa_in.dias_estimados,
                obra_id=nova_obra.id # Amarra a etapa na obra!
            )
            db.add(nova_etapa)
        db.commit()

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


@router.get("/{obra_id}/progresso")
def obter_progresso_obra(obra_id: int, db: Session = Depends(get_db)):
    etapas = db.query(models.EtapaObra).filter(models.EtapaObra.obra_id == obra_id).all()
    
    progresso_total = sum(etapa.peso_percentual for etapa in etapas if etapa.concluida)
            
    return {"progresso": progresso_total}
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas
from database import SessionLocal, get_db
from pydantic import BaseModel
from fastapi import HTTPException
from datetime import date

router = APIRouter()

@router.post("/orcamentos/", response_model=schemas.OrcamentoResponse)
def criar_orcamento(orcamento: schemas.OrcamentoCreate, db: Session = Depends(get_db)):
    novo_orcamento = models.orcamento(**orcamento.model_dump())

    db.add(novo_orcamento)
    db.commit()
    db.refresh(novo_orcamento)

    return novo_orcamento

@router.get("/orcamentos/", response_model=list[schemas.OrcamentoResponse])
def listar_orcamentos(db: Session = Depends(get_db)):
    return db.query(models.orcamento).all()

class StatusUpdate(BaseModel):
    status: str

@router.put("/orcamentos/{orcamento_id}/status")
def atualizar_status_orcamento(orcamento_id: int, atualizacao: StatusUpdate, db: Session = Depends(get_db)):
    orcamento = db.query(models.orcamento).filter(models.orcamento.id == orcamento_id).first()
    
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
        
    orcamento.status = atualizacao.status
    db.commit()
    
    return {"mensagem": "Status atualizado com sucesso!"}

@router.post("/orcamentos/{orcamento_id}/converter")
def converter_orcamento_em_obra(orcamento_id: int, dados: schemas.DadosConversao, db: Session = Depends(get_db)):
    orc = db.query(models.orcamento).filter(models.orcamento.id == orcamento_id).first()
    
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
        
    if orc.status == "Convertido em Obra":
        raise HTTPException(status_code=400, detail="Este orçamento já virou obra.")

    nova_obra = models.Obra(
        nome=f"{orc.nome_projeto} ({orc.cliente})",
        endereco=dados.endereco,
        data_inicio=dados.data_inicio,
        status="Planejamento",
        ambiente=dados.ambiente
    )
    db.add(nova_obra)
    
    orc.status = "Convertido em Obra"
    db.commit()
    return {"mensagem": "Obra criada com sucesso!"}

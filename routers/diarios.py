from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from database import get_db

router = APIRouter(prefix="/diarios", tags=["Diários"])


@router.post("/")
def criar_diario(diario_recebido: schemas.DiarioCreate, db: Session = Depends(get_db)):
    obra = db.query(models.Obra).filter(models.Obra.id == diario_recebido.obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")

    novo_diario = models.DiarioDeObra(
        data=diario_recebido.data,
        clima_manha=diario_recebido.clima_manha,
        clima_tarde=diario_recebido.clima_tarde,
        observacoes_gerais=diario_recebido.observacoes_gerais,
        local_dia=diario_recebido.local_dia,
        obra_id=diario_recebido.obra_id
    )
    db.add(novo_diario)
    db.commit()
    db.refresh(novo_diario)
    return novo_diario


@router.post("/completo", response_model=schemas.DiarioResponse)
def criar_diario_completo(dados: schemas.DiarioCompletoCreate, db: Session = Depends(get_db)):
    """Grava a capa, a equipe, os equipamentos e os gastos numa só transação: ou tudo, ou nada."""
    if not db.query(models.Obra).filter(models.Obra.id == dados.obra_id).first():
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    diario = models.DiarioDeObra(**dados.model_dump(exclude={"efetivos", "equipamentos", "gastos"}))
    diario.efetivos = [models.Efetivo(**e.model_dump()) for e in dados.efetivos]
    diario.equipamentos = [models.Equipamento(**e.model_dump()) for e in dados.equipamentos]
    diario.gastos = [models.Gasto(**g.model_dump()) for g in dados.gastos]
    db.add(diario)
    db.commit()
    db.refresh(diario)
    return diario


@router.get("/", response_model=list[schemas.DiarioResponse])
def listar_diarios(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.DiarioDeObra).offset(skip).limit(limit).all()


@router.delete("/{diario_id}")
def deletar_diario(diario_id: int, db: Session = Depends(get_db)):
    diario = db.query(models.DiarioDeObra).filter(models.DiarioDeObra.id == diario_id).first()
    if not diario:
        raise HTTPException(status_code=404, detail="Diário não encontrado")
    db.delete(diario)
    db.commit()
    return {"mensagem": "Diário removido com sucesso"}


@router.put("/{diario_id}")
def editar_diario(diario_id: int, dados: schemas.DiarioUpdate, db: Session = Depends(get_db)):
    diario = db.query(models.DiarioDeObra).filter(models.DiarioDeObra.id == diario_id).first()
    if not diario:
        raise HTTPException(status_code=404, detail="Diário não encontrado")
    diario.clima_manha = dados.clima_manha
    diario.clima_tarde = dados.clima_tarde
    diario.observacoes_gerais = dados.observacoes_gerais
    db.commit()
    return {"mensagem": "Diário atualizado com sucesso"}
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from database import get_db

router = APIRouter()

@router.post("/orcamentos/", response_model=schemas.OrcamentoResponse)
def criar_orcamento(orcamento: schemas.OrcamentoCreate, db: Session = Depends(get_db)):
    dados = orcamento.model_dump()
    # O total é sempre calculado aqui, para a conta nunca depender do que o cliente envia.
    dados["valor_total"] = round(dados["custo_material"] + dados["custo_mao_de_obra"] + dados["lucro"], 2)
    novo_orcamento = models.orcamento(**dados)

    db.add(novo_orcamento)
    db.commit()
    db.refresh(novo_orcamento)

    return novo_orcamento

@router.get("/orcamentos/", response_model=list[schemas.OrcamentoResponse])
def listar_orcamentos(db: Session = Depends(get_db)):
    return db.query(models.orcamento).all()

@router.put("/orcamentos/{orcamento_id}/status")
def atualizar_status_orcamento(orcamento_id: int, atualizacao: schemas.StatusOrcamentoUpdate, db: Session = Depends(get_db)):
    orcamento = db.query(models.orcamento).filter(models.orcamento.id == orcamento_id).first()
    
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    if orcamento.status == "Convertido em Obra":
        raise HTTPException(status_code=400, detail="Este orçamento já virou obra e não pode mudar de status.")

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

from database import SessionLocal, engine
import models
from datetime import date, timedelta

models.Base.metadata.create_all(bind=engine)

def injetar_etapas():
    db = SessionLocal()
    
    obra = db.query(models.Obra).first()
    
    if not obra:
        print("Nenhuma obra encontrada no banco de dados.")
        db.close()
        return

    print(f"🏗️ Injetando etapas na obra: {obra.nome} (ID: {obra.id})")
    
    etapa1 = models.EtapaObra(
        nome_etapa="1. Fundação",
        peso_percentual=20.0,
        dias_estimados=15,
        data_inicio_real=date.today() - timedelta(days=20),
        data_fim_real=date.today() - timedelta(days=2), 
        concluida=True,
        obra_id=obra.id
    )
    
    etapa2 = models.EtapaObra(
        nome_etapa="2. Alvenaria",
        peso_percentual=35.0,
        dias_estimados=30,
        data_inicio_real=date.today() - timedelta(days=1),
        data_fim_real=None, 
        concluida=False,
        obra_id=obra.id
    )
    
    db.add_all([etapa1, etapa2])
    db.commit()
    print("✅ Tabela criada e Etapas injetadas com sucesso!")
    
    db.close()

if __name__ == "__main__":
    injetar_etapas()
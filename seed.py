import random
from datetime import date, datetime, timedelta
from database import SessionLocal, engine
import models

def popular_banco_completo():
    # 1. RESET TOTAL (Apaga o banco antigo e recria com as colunas novas)
    print("🧹 Limpando banco de dados antigo...")
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    print("🚀 Iniciando a simulação de dados da Construtora...")
    hoje = date.today()

    # ==========================================
    # 2. GERANDO ORÇAMENTOS
    # ==========================================
    clientes = ["João Silva", "Condomínio Bela Vista", "Logística Alfa", "Prefeitura Municipal"]
    projetos = ["Casa Alto Padrão", "Reforma Portaria", "Galpão 1000m²", "Praça Pública"]
    status_orc = ["Aprovado", "Recusado", "Em análise"]

    for i in range(8):
        orc = models.orcamento(
            cliente=random.choice(clientes),
            nome_projeto=f"{random.choice(projetos)} - Lote {i}",
            custo_material=random.uniform(15000, 80000),
            custo_mao_de_obra=random.uniform(10000, 50000),
            lucro=random.uniform(5000, 20000),
            status=random.choice(status_orc)
        )
        orc.valor_total = orc.custo_material + orc.custo_mao_de_obra + orc.lucro
        db.add(orc)
    db.commit()

    # ==========================================
    # 3. GERANDO OBRAS E SEUS CRONOGRAMAS (ETAPAS)
    # ==========================================
    
    # CENÁRIO A: Obra no prazo (Em andamento) - 45 dias atrás
    obra1 = models.Obra(nome="Casa Condomínio (No Prazo)", endereco="Rua das Flores, 123", data_inicio=hoje - timedelta(days=45), status="Em andamento", ambiente="Aberto")
    db.add(obra1)
    db.commit()
    db.refresh(obra1)
    
    # Etapas Obra 1 (Total 100%)
    db.add_all([
        models.EtapaObra(nome_etapa="1. Fundação", peso_percentual=20.0, dias_estimados=15, data_inicio_real=obra1.data_inicio, data_fim_real=obra1.data_inicio + timedelta(days=14), concluida=True, obra_id=obra1.id), # Fez em 14 dias (adiantou 1)
        models.EtapaObra(nome_etapa="2. Alvenaria", peso_percentual=30.0, dias_estimados=30, data_inicio_real=obra1.data_inicio + timedelta(days=15), data_fim_real=None, concluida=False, obra_id=obra1.id), # Em andamento há 30 dias (no limite do prazo)
        models.EtapaObra(nome_etapa="3. Telhado", peso_percentual=15.0, dias_estimados=10, data_inicio_real=None, data_fim_real=None, concluida=False, obra_id=obra1.id),
        models.EtapaObra(nome_etapa="4. Acabamento", peso_percentual=35.0, dias_estimados=40, data_inicio_real=None, data_fim_real=None, concluida=False, obra_id=obra1.id)
    ])

    # CENÁRIO B: Obra Concluída Perfeita - 90 dias atrás
    obra2 = models.Obra(nome="Reforma Loja Shopping", endereco="Av. Comercial, 400", data_inicio=hoje - timedelta(days=90), status="Concluída", ambiente="Fechado")
    db.add(obra2)
    db.commit()
    db.refresh(obra2)

    db.add_all([
        models.EtapaObra(nome_etapa="1. Demolição", peso_percentual=30.0, dias_estimados=10, data_inicio_real=obra2.data_inicio, data_fim_real=obra2.data_inicio + timedelta(days=9), concluida=True, obra_id=obra2.id),
        models.EtapaObra(nome_etapa="2. Revestimento e Pintura", peso_percentual=70.0, dias_estimados=40, data_inicio_real=obra2.data_inicio + timedelta(days=10), data_fim_real=obra2.data_inicio + timedelta(days=50), concluida=True, obra_id=obra2.id)
    ])

    # CENÁRIO C: Obra MUITO Atrasada - 120 dias atrás
    obra3 = models.Obra(nome="Galpão Logístico (ATRASADA)", endereco="Rodovia BR, Km 12", data_inicio=hoje - timedelta(days=120), status="Atrasada", ambiente="Misto")
    db.add(obra3)
    db.commit()
    db.refresh(obra3)

    db.add_all([
        models.EtapaObra(nome_etapa="1. Terraplanagem", peso_percentual=15.0, dias_estimados=15, data_inicio_real=obra3.data_inicio, data_fim_real=obra3.data_inicio + timedelta(days=30), concluida=True, obra_id=obra3.id), # Era 15, levou 30!
        models.EtapaObra(nome_etapa="2. Estrutura Metálica", peso_percentual=45.0, dias_estimados=40, data_inicio_real=obra3.data_inicio + timedelta(days=35), data_fim_real=None, concluida=False, obra_id=obra3.id), # Era 40, já se passaram 85 dias e não acabou
        models.EtapaObra(nome_etapa="3. Piso Industrial", peso_percentual=40.0, dias_estimados=20, data_inicio_real=None, data_fim_real=None, concluida=False, obra_id=obra3.id)
    ])
    
    db.commit()

    # ==========================================
    # 4. PREENCHENDO OS DIÁRIOS DE OBRA
    # ==========================================
    obras_criadas = [(obra1, 45), (obra2, 50), (obra3, 120)] # Obra e quantidade de dias trabalhados
    climas = ["Sol", "Sol", "Sol", "Nublado", "Chuva", "Tempestade"]
    funcoes = ["Pedreiro", "Servente", "Soldador", "Engenheiro"]
    
    for obra, dias_totais in obras_criadas:
        print(f"🏗️ Gerando diários para a {obra.nome}...")
        
        for dia in range(dias_totais):
            data_diario = obra.data_inicio + timedelta(days=dia)
            
            # Pula alguns domingos
            if data_diario.weekday() == 6 and random.random() > 0.2:
                continue
                
            clima_m = random.choice(climas)
            clima_t = random.choice(climas)
            
            # Simulando o impacto da chuva nas observações
            if clima_t in ["Chuva", "Tempestade"] and obra.id == obra3.id:
                obs = "Máquinas atolaram na terraplanagem. Dia perdido."
            else:
                obs = "Trabalho seguiu o cronograma do dia." if random.random() > 0.3 else ""

            diario = models.DiarioDeObra(
                data=data_diario,
                clima_manha=clima_m,
                clima_tarde=clima_t,
                observacoes_gerais=obs,
                local_dia="Frente da Obra",
                obra_id=obra.id
            )
            db.add(diario)
            db.commit()
            db.refresh(diario)

            # Efetivo (1 a 5 equipes)
            for _ in range(random.randint(1, 3)):
                db.add(models.Efetivo(funcao=random.choice(funcoes), quantidade=random.randint(2, 6), horas_trabalhadas=8.0, diario_id=diario.id))

            # Equipamentos
            if random.random() > 0.5:
                db.add(models.Equipamento(nome_item=random.choice(["Betoneira", "Retroescavadeira", "Guindaste"]), tipo="Pesado", quantidade=1, diario_id=diario.id))

            # Gastos (R$ 100 a R$ 2000 por dia)
            for _ in range(random.randint(0, 2)):
                db.add(models.Gasto(item=random.choice(["Cimento CSN", "Aço CA50", "Tijolo Baiano", "Areia fina"]), categoria="Material", valor=random.uniform(100.0, 2000.0), diario_id=diario.id))
            
            db.commit()

    print("✅ Banco de dados populado com Sucesso! 3 Obras detalhadas prontas para o Analista IA.")
    db.close()

if __name__ == "__main__":
    popular_banco_completo()
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from google import genai 
from database import get_db
import models 
import schemas

load_dotenv()
cliente_ia = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

router = APIRouter(prefix="/ia", tags=["Analista IA"])

@router.post("/chat")
def conversar_com_ia(chat_req: schemas.ChatRequest, db: Session = Depends(get_db)):
    
    obras = db.query(models.Obra).all()
    dados_obras = []
    
    for obra in obras:
        diarios = db.query(models.DiarioDeObra).filter(models.DiarioDeObra.obra_id == obra.id).all()
        
        total_gasto = 0
        hist_gastos = []
        hist_efetivo = []
        hist_equipamentos = []
        
        for diario in diarios:
            data_str = diario.data.strftime("%d/%m/%Y") if hasattr(diario.data, 'strftime') else str(diario.data)
            
            gastos = db.query(models.Gasto).filter(models.Gasto.diario_id == diario.id).all()
            for g in gastos:
                total_gasto += g.valor
                hist_gastos.append(f"[{data_str}] {g.item}: R$ {g.valor}")
                
            efetivos = db.query(models.Efetivo).filter(models.Efetivo.diario_id == diario.id).all()
            for e in efetivos:
                hist_efetivo.append(f"[{data_str}] {e.quantidade}x {e.funcao}")
                
            equipamentos = db.query(models.Equipamento).filter(models.Equipamento.diario_id == diario.id).all()
            for eq in equipamentos:
                hist_equipamentos.append(f"[{data_str}] {eq.quantidade}x {eq.nome_item}")

        resumo_obra = f"""
        ### OBRA: {obra.nome}
        - Total de Diários Preenchidos: {len(diarios)}
        - Custo Total Acumulado: R$ {total_gasto:.2f}
        """
        
        if hist_gastos:
            resumo_obra += f"\n- Histórico de Gastos: {', '.join(hist_gastos)}"
        if hist_efetivo:
            resumo_obra += f"\n- Histórico de Efetivo: {', '.join(hist_efetivo)}"
        if hist_equipamentos:
            resumo_obra += f"\n- Histórico de Equipamentos: {', '.join(hist_equipamentos)}"
            
        dados_obras.append(resumo_obra)
    
    contexto_completo = "RELATÓRIO GERAL DO SISTEMA:\n\n" + "\n\n".join(dados_obras)
    

    
    texto_memoria = ""
    if chat_req.historico:
        texto_memoria = "HISTÓRICO DA CONVERSA RECENTE:\n"
        for msg in chat_req.historico[-4:]: # Pega só as últimas 4 mensagens para não sobrecarregar
            quem = "Chefe" if msg["role"] == "user" else "Assistente"
            texto_memoria += f"{quem}: {msg['content']}\n"
    
    prompt_sistema = f"""
    Você é um Engenheiro Assistente Sênior e Analista de Dados de uma construtora. 
    Sua função é fornecer respostas precisas, analíticas e diretas ao dono da empresa.
    
    REGRAS OBRIGATÓRIAS:
    1. Baseie-se EXCLUSIVAMENTE nos dados fornecidos abaixo.
    2. Se a resposta exigir cálculos, faça-os baseados nos dados.
    3. Se não houver dados sobre a pergunta, informe educadamente.
    
    DADOS DO SISTEMA:
    {contexto_completo}
    
    {texto_memoria}
    
    PERGUNTA ATUAL DO CHEFE:
    {chat_req.mensagem}
    """

    
    try:
        resposta = cliente_ia.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_sistema,
        )
        return {"resposta": resposta.text}
    except Exception as e:
        return {"resposta": f"Desculpe chefe, erro no servidor da IA: {str(e)}"}
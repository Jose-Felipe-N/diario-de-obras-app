from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai 
from google.genai import types
from database import get_db
import models 
import schemas

load_dotenv()
cliente_ia = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

router = APIRouter(prefix="/ia", tags=["Analista IA"])


@router.get("/obras_disponiveis")
def listar_obras(db: Session = Depends(get_db)):
    obras = db.query(models.Obra.id, models.Obra.nome).all()
    return [{"id": o.id, "nome": o.nome} for o in obras]


@router.post("/chat")
def conversar_com_ia(chat_req: schemas.ChatRequest, db: Session = Depends(get_db)):
    
    if chat_req.obra_id:
        obras = db.query(models.Obra).filter(models.Obra.id == chat_req.obra_id).all()
    else:
        obras = db.query(models.Obra).all()
    orcamentos = db.query(models.orcamento).all()
    dados_obras = []
    dados_orcamentos = []
    
    for orc in orcamentos:
        dados_orcamentos.append(
            f"Projeto: {orc.nome_projeto} | Cliente: {orc.cliente} | "
            f"Previsto Material: R$ {orc.custo_material:.2f} | "
            f"Previsto Mão de Obra: R$ {orc.custo_mao_de_obra:.2f} | "
            f"Total Orcado: R$ {orc.valor_total:.2f} | Status: {orc.status}"
        )

    for obra in obras:
        diarios = db.query(models.DiarioDeObra).filter(models.DiarioDeObra.obra_id == obra.id).all()
        
        total_gasto = 0
        hist_detalhado = []
        
        for diario in diarios:
            data_str = diario.data.strftime("%d/%m/%Y") if hasattr(diario.data, 'strftime') else str(diario.data)
            
            info_dia = {
                "data": data_str,
                "clima": f"Manhã: {diario.clima_manha}, Tarde: {diario.clima_tarde}",
                "local": diario.local_dia,
                "obs": diario.observacoes_gerais,
                "gastos": [],
                "efetivo": [],
                "equipamentos": []
            }

            gastos = db.query(models.Gasto).filter(models.Gasto.diario_id == diario.id).all()
            for g in gastos:
                total_gasto += g.valor
                info_dia["gastos"].append(f"{g.item} ({g.categoria}): R$ {g.valor:.2f}")
                
            efetivos = db.query(models.Efetivo).filter(models.Efetivo.diario_id == diario.id).all()
            for e in efetivos:
                info_dia["efetivo"].append(f"{e.quantidade}x {e.funcao} ({e.horas_trabalhadas}h cada)")
                
            equipamentos = db.query(models.Equipamento).filter(models.Equipamento.diario_id == diario.id).all()
            for eq in equipamentos:
                info_dia["equipamentos"].append(f"{eq.quantidade}x {eq.nome_item} ({eq.tipo})")
            
            hist_detalhado.append(info_dia)

        resumo_obra = f"""
        ### OBRA: {obra.nome}
        - Ambiente: {obra.ambiente} | Status: {obra.status} | Início: {obra.data_inicio}
        - Endereço: {obra.endereco}
        - Financeiro: R$ {total_gasto:.2f} acumulados em {len(diarios)} diários.
        - Histórico de Atividades: {json.dumps(hist_detalhado)}
        """
        dados_obras.append(resumo_obra)
    
    contexto_completo = "DADOS DE ORÇAMENTOS:\n" + "\n".join(dados_orcamentos)
    contexto_completo += "\n\nRELATÓRIO DE EXECUÇÃO:\n" + "\n".join(dados_obras)
    
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    texto_memoria = ""
    if chat_req.historico:
        texto_memoria = "HISTÓRICO DA CONVERSA RECENTE:\n"
        for msg in chat_req.historico[-4:]:
            quem = "Chefe" if msg["role"] == "user" else "Assistente"
            texto_memoria += f"{quem}: {msg['content']}\n"
    
    prompt_sistema = f"""
    Você é um Engenheiro Assistente Sênior da construtora. Hoje é {data_atual}.
    
    REGRAS DE CONDUTA (GUARDRAILS):
    1. Use os dados de Orçamentos para comparar com os Gastos Reais se solicitado.
    2. Analise clima e observações para justificar atrasos ou produtividade.
    3. Para gráficos, agrupe dados numericamente por categoria ou data.
    4. FOCO RESTRITO: O seu conhecimento está estritamente limitado aos DADOS DO SISTEMA abaixo e a assuntos de engenharia civil/construção. Se o usuário perguntar qualquer coisa fora desse escopo (como programação, receitas, atualidades, piadas, etc.), VOCÊ DEVE RECUSAR a resposta. Diga educadamente algo como: "Desculpe chefe, mas como Assistente de Engenharia da construtora, meu foco é exclusivo nos dados das nossas obras e orçamentos."
    
    SISTEMA:
    {contexto_completo}
    
    {texto_memoria}
    
    PERGUNTA:
    {chat_req.mensagem}

    SAÍDA JSON:
    {{
        "resposta": "Texto detalhado",
        "gerar_grafico": boolean,
        "tipo_grafico": "barras", // ESCOLHA ENTRE: "barras", "pizza" ou "linha"
        "titulo_grafico": "Título",
        "dados_grafico": {{"Chave": valor}}
    }}
    """

    try:
        resposta = cliente_ia.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_sistema,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(resposta.text)
    except Exception as e:
        return {"resposta": f"Erro técnico: {str(e)}", "gerar_grafico": False}
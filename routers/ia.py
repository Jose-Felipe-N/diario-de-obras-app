import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from google.genai import errors as erros_do_gemini
from sqlalchemy.orm import Session

import gemini
import models
import schemas
from analista.agente import ErroDoAssistente, responder
from database import get_db

router = APIRouter(prefix="/ia", tags=["Analista IA"])
log = logging.getLogger(__name__)


@router.get("/obras_disponiveis")
def listar_obras(db: Session = Depends(get_db)):
    obras = db.query(models.Obra.id, models.Obra.nome).all()
    return [{"id": o.id, "nome": o.nome} for o in obras]


def falha(status, mensagem, codigo):
    """Resposta de erro no mesmo formato da resposta normal, para a tela mostrar a mensagem."""
    return JSONResponse(status_code=status,
                        content={"resposta": mensagem, "gerar_grafico": False, "erro": codigo})


@router.post("/chat")
def conversar_com_ia(chat_req: schemas.ChatRequest, db: Session = Depends(get_db)):
    try:
        return responder(db, chat_req.mensagem, chat_req.historico, chat_req.obra_id)
    except gemini.CotaEsgotada as e:
        return falha(429, str(e), "cota_diaria")
    except ErroDoAssistente as e:
        return falha(e.status, str(e), "resposta_invalida")
    except erros_do_gemini.APIError as e:
        log.warning("Erro da API do Gemini (%s): %s", e.code, e)
        if e.code == 429:
            return falha(429, "Muitas perguntas em pouco tempo. Espere um minuto e tente de novo.", "limite_da_api")
        if e.code in (500, 503, 504):
            return falha(503, "O assistente está sobrecarregado agora. Tente de novo em instantes.", "indisponivel")
        return falha(502, "O assistente não conseguiu responder agora. Tente de novo.", "erro_da_api")
    except Exception:
        log.exception("Falha inesperada no Analista IA")
        return falha(500, "Ocorreu um erro inesperado no assistente. Tente de novo.", "erro_interno")

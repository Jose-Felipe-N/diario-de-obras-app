import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from google.genai import errors as erros_do_gemini
from sqlalchemy.orm import Session

import config
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
        if e.code == 400 and "response mime type" in str(e):
            log.error("O modelo %s não aceita ferramentas com resposta em JSON; use um modelo Gemini 3 "
                      "(variável GEMINI_MODEL).", config.GEMINI_MODEL)
            return falha(500, f"O assistente está mal configurado: o modelo {config.GEMINI_MODEL} não é compatível. "
                              "Configure um modelo Gemini 3 em GEMINI_MODEL.", "modelo_incompativel")
        return falha(502, "O assistente não conseguiu responder agora. Tente de novo.", "erro_da_api")
    except Exception:
        log.exception("Falha inesperada no Analista IA")
        return falha(500, "Ocorreu um erro inesperado no assistente. Tente de novo.", "erro_interno")


@router.post("/feedback")
def registrar_feedback(dados: schemas.FeedbackRequest):
    """Guarda a avaliação 👍/👎 de uma resposta numa linha do arquivo de feedback."""
    registro = {"quando": datetime.now(timezone.utc).isoformat(timespec="seconds"), **dados.model_dump()}
    config.FEEDBACK_ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    with open(config.FEEDBACK_ARQUIVO, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return {"mensagem": "Avaliação registrada."}

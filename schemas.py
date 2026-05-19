from pydantic import BaseModel
from datetime import date
from typing import Optional


# ── Obras ──────────────────────────────────────────────────────────────────────

class ObraCreate(BaseModel):
    nome: str
    endereco: Optional[str] = None
    data_inicio: Optional[date] = None
    status: Optional[str] = "Em andamento"
    ambiente: Optional[str] = "Aberto"


class StatusUpdate(BaseModel):
    status: str


# ── Diários ────────────────────────────────────────────────────────────────────

class DiarioCreate(BaseModel):
    data: date
    clima_manha: Optional[str] = None
    clima_tarde: Optional[str] = None
    observacoes_gerais: Optional[str] = None
    local_dia: Optional[str] = None
    obra_id: int


class DiarioUpdate(BaseModel):
    clima_manha: Optional[str] = None
    clima_tarde: Optional[str] = None
    observacoes_gerais: Optional[str] = None


# ── Efetivos ───────────────────────────────────────────────────────────────────

class EfetivoCreate(BaseModel):
    funcao: str
    quantidade: int
    horas_trabalhadas: float
    diario_id: int


class EfetivoResponse(EfetivoCreate):
    id: int
    class Config:
        from_attributes = True


# ── Equipamentos ───────────────────────────────────────────────────────────────

class EquipamentoCreate(BaseModel):
    nome_item: str
    tipo: str
    quantidade: int
    diario_id: int


class EquipamentoResponse(EquipamentoCreate):
    id: int
    class Config:
        from_attributes = True


# ── Gastos ─────────────────────────────────────────────────────────────────────

class GastoCreate(BaseModel):
    item: str
    categoria: str
    valor: float
    diario_id: int


class GastoResponse(GastoCreate):
    id: int
    class Config:
        from_attributes = True


# ── Responses compostos ────────────────────────────────────────────────────────

class DiarioResponse(DiarioCreate):
    id: int
    efetivos: list[EfetivoResponse] = []
    equipamentos: list[EquipamentoResponse] = []
    gastos: list[GastoResponse] = []
    class Config:
        from_attributes = True


class ObraResponse(ObraCreate):
    id: int
    diarios: list[DiarioResponse] = []
    class Config:
        from_attributes = True

# ── Orçamentos ──────────────────────────────────────────────────────────────────

class OrcamentoCreate(BaseModel):
    cliente: str
    nome_projeto: str
    custo_material: float
    custo_mao_de_obra: float
    lucro: float
    valor_total: float

class OrcamentoResponse(OrcamentoCreate):
    id: int
    status: str

    class Config:
        from_attributes = True

class DadosConversao(BaseModel):
    endereco: str
    ambiente: str
    data_inicio: date

# ── Analista de IA ──────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    mensagem: str
    historico: list = []
    obra_id: Optional[int] = None  # Se for None, a IA analisa todas as obras. Se tiver ID, ela foca em uma só.

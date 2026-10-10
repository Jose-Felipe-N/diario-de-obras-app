from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List, Literal

# Valores aceitos pela API. A tela exibe rótulos longos ("Fechado (Coberto)"),
# mas grava só estes; qualquer outro valor é recusado com 422.
Ambiente = Literal["Aberto", "Fechado", "Misto"]
LocalDia = Literal["Interior", "Exterior"]


# ── Etapas ──────────────────────────────────────────────────────────────────
class EtapaCreate(BaseModel):
    nome_etapa: str
    peso_percentual: float
    dias_estimados: int

# ── Obras ──────────────────────────────────────────────────────────────────────

class ObraCreate(BaseModel):
    nome: str
    endereco: Optional[str] = None
    data_inicio: Optional[date] = None
    status: Optional[str] = "Em andamento"
    ambiente: Ambiente = "Aberto"
    etapas: List[EtapaCreate] = []


class StatusUpdate(BaseModel):
    status: str


# ── Diários ────────────────────────────────────────────────────────────────────

class DiarioCreate(BaseModel):
    data: date
    clima_manha: Optional[str] = None
    clima_tarde: Optional[str] = None
    observacoes_gerais: Optional[str] = None
    local_dia: Optional[LocalDia] = None
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

StatusOrcamento = Literal["Em análise", "Aprovado", "Recusado", "Convertido em Obra"]
# "Convertido em Obra" só é definido pelo /converter, junto com a criação da obra.
StatusOrcamentoManual = Literal["Em análise", "Aprovado", "Recusado"]


class OrcamentoCreate(BaseModel):
    cliente: str
    nome_projeto: str
    custo_material: float = Field(ge=0)
    custo_mao_de_obra: float = Field(ge=0)
    # Lucro em reais. A tela recebe a porcentagem de markup sobre o custo e converte.
    # O valor_total não é recebido: o servidor calcula material + mão de obra + lucro.
    lucro: float = Field(ge=0)


class OrcamentoResponse(OrcamentoCreate):
    id: int
    valor_total: float
    status: StatusOrcamento

    class Config:
        from_attributes = True


class StatusOrcamentoUpdate(BaseModel):
    status: StatusOrcamentoManual

class DadosConversao(BaseModel):
    endereco: str
    ambiente: Ambiente
    data_inicio: date

# ── Analista de IA ──────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    mensagem: str
    historico: list = []
    obra_id: Optional[int] = None  # Se for None, a IA analisa todas as obras. Se tiver ID, ela foca em uma só.

"""Ferramentas que o modelo pode chamar. Cada uma roda SQL no servidor e devolve dados compactos.

O escopo da conversa é imposto aqui, não no prompt: com uma obra selecionada, todas as
ferramentas ficam presas a ela, e um pedido de outra obra é recusado.
"""

import unicodedata
from datetime import date, timedelta

from sqlalchemy.orm import Session

import config
import models

MAX_DIAS_POR_CONSULTA = 31
HORAS_DIA_PARADO = 2
DIAS_DA_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


class ErroDeFerramenta(Exception):
    """Pedido inválido para a ferramenta; a mensagem volta para o modelo."""


def _normalizar(texto):
    sem_acento = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn").lower().strip()


def _data(texto, nome):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ErroDeFerramenta(f"'{nome}' deve ser uma data no formato AAAA-MM-DD.")


def _reais(valor):
    return round(float(valor or 0), 2)


class Ferramentas:
    def __init__(self, db: Session, obra_id=None):
        self.db = db
        self.obra_fixa = db.get(models.Obra, obra_id) if obra_id else None

    # ── escopo ────────────────────────────────────────────────────────────────

    def _obras_do_escopo(self):
        if self.obra_fixa:
            return [self.obra_fixa]
        return self.db.query(models.Obra).order_by(models.Obra.id).all()

    def _obra(self, nome=None, obrigatoria=True):
        """A obra pedida, respeitando o escopo da conversa."""
        if self.obra_fixa:
            if nome and _normalizar(nome) not in _normalizar(self.obra_fixa.nome) \
                    and _normalizar(self.obra_fixa.nome) not in _normalizar(nome):
                raise ErroDeFerramenta(
                    f"Esta conversa está restrita à obra '{self.obra_fixa.nome}'. Para consultar '{nome}', "
                    "o usuário precisa selecionar essa obra.")
            return self.obra_fixa
        if not nome:
            if obrigatoria:
                raise ErroDeFerramenta("Informe a obra. Obras disponíveis: " +
                                       ", ".join(o.nome for o in self._obras_do_escopo()) + ".")
            return None
        encontradas = [o for o in self._obras_do_escopo() if _normalizar(nome) in _normalizar(o.nome)
                       or _normalizar(o.nome) in _normalizar(nome)]
        if len(encontradas) != 1:
            raise ErroDeFerramenta(f"Obra '{nome}' não encontrada. Obras disponíveis: " +
                                   ", ".join(o.nome for o in self._obras_do_escopo()) + ".")
        return encontradas[0]

    def _periodo(self, inicio, fim, limite=None):
        hoje = config.hoje()
        inicio = _data(inicio, "inicio") if inicio else None
        fim = _data(fim, "fim") if fim else hoje
        if inicio and inicio > fim:
            raise ErroDeFerramenta("'inicio' é depois de 'fim'.")
        if limite and inicio and (fim - inicio).days + 1 > limite:
            raise ErroDeFerramenta(f"Peça períodos de até {limite} dias.")
        return inicio, fim

    def _diarios(self, obras, inicio, fim):
        consulta = self.db.query(models.DiarioDeObra).filter(
            models.DiarioDeObra.obra_id.in_([o.id for o in obras]), models.DiarioDeObra.data <= fim)
        if inicio:
            consulta = consulta.filter(models.DiarioDeObra.data >= inicio)
        return consulta.order_by(models.DiarioDeObra.data).all()

    # ── ferramentas ───────────────────────────────────────────────────────────

    def listar_obras(self):
        return {"obras": [{**self._resumo(o), "etapas": self._etapas(o)} for o in self._obras_do_escopo()]}

    def cronograma(self, obra=None):
        o = self._obra(obra)
        return {**self._resumo(o), "etapas": self._etapas(o)}

    def diarios(self, inicio, fim, obra=None):
        o = self._obra(obra)
        inicio, fim = self._periodo(inicio, fim, MAX_DIAS_POR_CONSULTA)
        registros = self._diarios([o], inicio, fim)
        com_diario = {d.data for d in registros}
        return {
            "obra": o.nome, "periodo": [inicio.isoformat(), fim.isoformat()],
            "datas_sem_diario": [(inicio + timedelta(i)).isoformat() for i in range((fim - inicio).days + 1)
                                 if inicio + timedelta(i) not in com_diario],
            "diarios": [self._diario(d) for d in registros],
        }

    def gastos(self, obra=None, inicio=None, fim=None, categoria=None, item=None):
        obras = [self._obra(obra)] if (obra or self.obra_fixa) else self._obras_do_escopo()
        inicio, fim = self._periodo(inicio, fim)
        registros = self._diarios(obras, inicio, fim)
        lancamentos = [(d, g) for d in registros for g in d.gastos
                       if (not categoria or _normalizar(categoria) == _normalizar(g.categoria))
                       and (not item or _normalizar(item) == _normalizar(g.item))]
        por_obra, por_categoria, por_item = {}, {}, {}
        for d, g in lancamentos:
            por_obra[d.obra.nome] = por_obra.get(d.obra.nome, 0) + g.valor
            por_categoria[g.categoria] = por_categoria.get(g.categoria, 0) + g.valor
            por_item[g.item] = por_item.get(g.item, 0) + g.valor
        resultado = {
            "periodo": [inicio.isoformat() if inicio else "início da obra", fim.isoformat()],
            "filtros": {"obra": [o.nome for o in obras], "categoria": categoria, "item": item},
            "diarios_no_periodo": len(registros),
            "lancamentos": len(lancamentos),
            "total": _reais(sum(g.valor for _, g in lancamentos)),
            "por_obra": {k: _reais(v) for k, v in por_obra.items()},
            "por_categoria": {k: _reais(v) for k, v in por_categoria.items()},
            "por_item": {k: _reais(v) for k, v in por_item.items()},
        }
        if not registros:
            resultado["aviso"] = "Não há diários nesse período: isso é falta de registro, não gasto zero."
        elif not lancamentos:
            resultado["aviso"] = "Há diários no período, mas nenhum lançamento com esses filtros: o gasto foi zero."
        return resultado

    def observacoes(self, obra=None, inicio=None, fim=None):
        obras = [self._obra(obra)] if (obra or self.obra_fixa) else self._obras_do_escopo()
        inicio, fim = self._periodo(inicio, fim)
        return {"observacoes": [{"obra": d.obra.nome, "data": d.data.isoformat(), "texto": d.observacoes_gerais}
                                for d in self._diarios(obras, inicio, fim) if (d.observacoes_gerais or "").strip()]}

    def orcamento(self, obra=None):
        o = self._obra(obra)
        ligados = self.db.query(models.orcamento).filter(models.orcamento.obra_id == o.id).all()
        if not ligados:
            return {"obra": o.nome, "aviso": "Nenhum orçamento ligado a esta obra."}
        material = sum(g.valor for d in o.diarios for g in d.gastos if g.categoria == "Material de Construção")
        return {
            "obra": o.nome,
            "orcamentos": [{
                "projeto": orc.nome_projeto, "cliente": orc.cliente, "status": orc.status,
                "custo_material": _reais(orc.custo_material), "custo_mao_de_obra": _reais(orc.custo_mao_de_obra),
                "lucro": _reais(orc.lucro), "valor_total": _reais(orc.valor_total),
            } for orc in ligados],
            "material_lancado": _reais(material),
            "percentual_do_material_orcado": round(material / ligados[0].custo_material * 100, 1)
            if ligados[0].custo_material else None,
            "nota": "A equipe própria é registrada em horas, sem custo em reais; compare material com material.",
        }

    # ── formatos ──────────────────────────────────────────────────────────────

    def _resumo(self, o):
        ultimo = max((d.data for d in o.diarios), default=None)
        return {"obra": o.nome, "status": o.status, "ambiente": o.ambiente,
                "inicio": o.data_inicio.isoformat() if o.data_inicio else None,
                "progresso_fisico": sum(e.peso_percentual or 0 for e in o.etapas if e.concluida),
                "ultimo_diario": ultimo.isoformat() if ultimo else None}

    def _etapas(self, o):
        hoje = config.hoje()
        etapas = []
        for e in o.etapas:
            item = {"etapa": e.nome_etapa, "peso": e.peso_percentual, "dias_estimados": e.dias_estimados,
                    "concluida": bool(e.concluida)}
            if e.data_inicio_real:
                fim = e.data_fim_real or hoje
                dias = (fim - e.data_inicio_real).days
                item.update(inicio=e.data_inicio_real.isoformat(),
                            fim=e.data_fim_real.isoformat() if e.data_fim_real else None, dias_decorridos=dias,
                            situacao="atrasada" if dias > (e.dias_estimados or 0) else "no prazo")
            else:
                item["situacao"] = "não iniciada"
            etapas.append(item)
        return etapas

    def _diario(self, d):
        horas = [e.horas_trabalhadas for e in d.efetivos]
        return {
            "data": d.data.isoformat(), "dia_da_semana": DIAS_DA_SEMANA[d.data.weekday()],
            "clima": {"manha": d.clima_manha, "tarde": d.clima_tarde}, "local": d.local_dia,
            "efetivo": [{"funcao": e.funcao, "quantidade": e.quantidade, "horas": e.horas_trabalhadas} for e in d.efetivos],
            "pessoas": sum(e.quantidade for e in d.efetivos),
            "dia_parado": not horas or max(horas) <= HORAS_DIA_PARADO,
            "equipamentos": [{"nome": q.nome_item, "quantidade": q.quantidade} for q in d.equipamentos],
            "gastos": [{"item": g.item, "categoria": g.categoria, "valor": _reais(g.valor)} for g in d.gastos],
            "observacao": d.observacoes_gerais or "",
        }


# Declarações enviadas ao modelo (JSON Schema). A obra é opcional: com uma obra
# selecionada, o servidor a impõe; na visão geral, o modelo informa o nome.
OBRA = {"type": "string", "description": "Nome da obra. Opcional quando a conversa já tem uma obra selecionada."}
DATA = {"type": "string", "description": "Data no formato AAAA-MM-DD."}

DECLARACOES = [
    {"name": "listar_obras",
     "description": "Lista as obras com status, progresso físico, último diário e situação de prazo de cada etapa.",
     "parameters_json_schema": {"type": "object", "properties": {}}},
    {"name": "cronograma",
     "description": "Etapas de uma obra: dias decorridos contra estimados, situação (atrasada, no prazo, não iniciada) e progresso.",
     "parameters_json_schema": {"type": "object", "properties": {"obra": OBRA}}},
    {"name": "diarios",
     "description": "Diários de uma obra num período de até 31 dias: clima, local, equipe, horas, se o dia foi parado, "
                    "equipamentos, gastos e observação. Também lista as datas sem diário.",
     "parameters_json_schema": {"type": "object", "properties": {"obra": OBRA, "inicio": DATA, "fim": DATA},
                                "required": ["inicio", "fim"]}},
    {"name": "gastos",
     "description": "Soma os gastos lançados nos diários, com filtros opcionais de obra, período, categoria e item. "
                    "Distingue falta de registro de gasto zero. Sem obra na visão geral, soma todas as obras.",
     "parameters_json_schema": {"type": "object", "properties": {
         "obra": OBRA, "inicio": DATA, "fim": DATA,
         "categoria": {"type": "string", "description": "Ex.: Material de Construção, Mão de Obra Externa, Locação."},
         "item": {"type": "string", "description": "Ex.: Cimento, Tijolo, Aluguel de guindaste."}}}},
    {"name": "observacoes",
     "description": "Textos das observações escritas nos diários (só os dias que têm texto), com obra e data. "
                    "Use para perguntas sobre acontecimentos, problemas e pedidos.",
     "parameters_json_schema": {"type": "object", "properties": {"obra": OBRA, "inicio": DATA, "fim": DATA}}},
    {"name": "orcamento",
     "description": "Orçamento ligado a uma obra e o material lançado nos diários comparado ao material orçado.",
     "parameters_json_schema": {"type": "object", "properties": {"obra": OBRA}}},
]


def executar(ferramentas, nome, argumentos):
    """Executa uma ferramenta pelo nome; erros de uso voltam para o modelo como texto."""
    if nome not in {d["name"] for d in DECLARACOES}:
        return {"erro": f"Ferramenta desconhecida: {nome}."}
    try:
        return getattr(ferramentas, nome)(**(argumentos or {}))
    except ErroDeFerramenta as e:
        return {"erro": str(e)}
    except TypeError:
        return {"erro": f"Argumentos inválidos para {nome}: {argumentos}."}

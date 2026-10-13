"""Textos da tela do Analista IA (sem Streamlit, para poder testar)."""

from formatos import data_br

PERGUNTAS_DE_EXEMPLO = {
    None: ["Qual obra está atrasada?", "Quanto gastamos de material este mês?", "Algum fornecedor atrasou entrega?"],
    "obra": ["O que aconteceu ontem?", "A obra está dentro do orçado?", "Teve algum problema com equipamento?"],
}


def _periodo(argumentos):
    inicio, fim = argumentos.get("inicio"), argumentos.get("fim")
    if inicio and fim:
        return f"de {data_br(inicio)} a {data_br(fim)}" if inicio != fim else f"de {data_br(inicio)}"
    if inicio:
        return f"a partir de {data_br(inicio)}"
    if fim:
        return f"até {data_br(fim)}"
    return ""


def _juntar(*partes):
    return " ".join(p for p in partes if p)


def descrever_ferramenta(nome, argumentos):
    """Uma linha legível para o engenheiro sobre o que o assistente consultou."""
    a = argumentos or {}
    obra = f"({a['obra']})" if a.get("obra") else ""
    periodo = _periodo(a)
    if nome == "listar_obras":
        return "Lista das obras e situação do cronograma"
    if nome == "cronograma":
        return _juntar("Cronograma das etapas", obra)
    if nome == "diarios":
        return _juntar("Diários", periodo, obra)
    if nome == "gastos":
        filtro = " · ".join(v for v in (a.get("categoria"), a.get("item")) if v)
        return _juntar("Gastos", f"de {filtro}" if filtro else "", periodo, obra)
    if nome == "buscar_observacoes":
        return _juntar(f"Busca por tema nas observações: \"{a.get('consulta', '')}\"", periodo, obra)
    if nome == "observacoes":
        return _juntar("Observações dos diários", periodo or "de todo o período", obra)
    if nome == "orcamento":
        return _juntar("Orçamento ligado à obra", obra)
    return nome


def descrever_fontes(uso):
    """Lista sem repetição do que foi consultado para uma resposta (vazia se nada foi consultado)."""
    linhas = [descrever_ferramenta(f["nome"], f.get("argumentos")) for f in (uso or {}).get("ferramentas", [])]
    return list(dict.fromkeys(linhas))

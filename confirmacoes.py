"""Textos e regras das confirmações de exclusão da tela (sem Streamlit, para poder testar)."""

from formatos import data_br


def nome_confere(digitado, nome):
    """A exclusão da obra só libera quando o usuário digita o nome dela (sem diferenciar maiúsculas)."""
    return bool(digitado) and digitado.strip().casefold() == nome.strip().casefold()


def resumo_exclusao_obra(obra):
    diarios = obra.get("diarios") or []
    if not diarios:
        return f"Isto apaga a obra **{obra['nome']}**, que ainda não tem diários. Não dá para desfazer."
    datas = sorted(d["data"] for d in diarios)
    periodo = f"de {data_br(datas[0])} a {data_br(datas[-1])}" if len(datas) > 1 else f"de {data_br(datas[0])}"
    plural = "diário" if len(diarios) == 1 else "diários"
    return (f"Isto apaga a obra **{obra['nome']}** e **{len(diarios)} {plural}** ({periodo}), com equipe, "
            "equipamentos e gastos. Não dá para desfazer.")


def resumo_exclusao_diario(diario, obra_nome):
    trabalhadores = sum(e["quantidade"] for e in diario.get("efetivos") or [])
    gastos = sum(g["valor"] for g in diario.get("gastos") or [])
    valor = f"R$ {gastos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (f"Isto apaga o diário de **{data_br(diario['data'])}** da obra **{obra_nome}** "
            f"({trabalhadores} trabalhador(es), {valor} em gastos). Não dá para desfazer.")

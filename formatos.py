"""Datas no formato brasileiro para a tela (sem depender do idioma do sistema)."""

from datetime import date

DIAS_DA_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]


def data_br(iso):
    """'2026-10-07' -> '07/10/2026'."""
    ano, mes, dia = iso[:10].split("-")
    return f"{dia}/{mes}/{ano}"


def data_com_semana(iso):
    """'2026-10-07' -> 'qua, 07/10/2026'."""
    return f"{DIAS_DA_SEMANA[date.fromisoformat(iso[:10]).weekday()]}, {data_br(iso)}"


def mes_br(ano_mes):
    """'2026-10' -> 'outubro de 2026'."""
    ano, mes = ano_mes.split("-")
    return f"{MESES[int(mes) - 1]} de {ano}"

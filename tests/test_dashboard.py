"""O alerta de clima do dashboard só aparece para trabalho feito ao ar livre."""

from datetime import date

import pytest


@pytest.mark.parametrize("ambiente, local, clima, alerta", [
    ("Aberto", "Exterior", "Chuva", True),
    ("Aberto", "Exterior", "Sol", False),
    ("Fechado", "Interior", "Tempestade", False),
    ("Misto", "Interior", "Chuva", False),
    ("Misto", "Exterior", "Tempestade", True),
    ("Fechado", None, "Chuva", False),   # diário antigo sem local: vale o ambiente da obra
    ("Misto", None, "Chuva", True),
])
def test_alerta_de_clima_respeita_ambiente_e_local(cliente, ambiente, local, clima, alerta):
    obra_id = cliente.post("/obras/", json={"nome": "Obra", "ambiente": ambiente}).json()["id"]
    diario = {"data": date.today().isoformat(), "clima_manha": "Sol", "clima_tarde": clima, "obra_id": obra_id}
    if local:
        diario["local_dia"] = local
    assert cliente.post("/diarios/", json=diario).status_code == 200

    alertas = cliente.get("/dashboard/").json()["alertas_clima"]
    assert bool(alertas) is alerta


def test_obras_em_andamento_sem_diario_hoje(cliente):
    ids = {}
    for nome, status in (("Casa", "Em andamento"), ("Galpão", "Em andamento"), ("Loja", "Concluída")):
        ids[nome] = cliente.post("/obras/", json={"nome": nome, "ambiente": "Aberto", "status": status}).json()["id"]
    cliente.post("/diarios/", json={"data": date.today().isoformat(), "obra_id": ids["Casa"]})

    pendentes = cliente.get("/dashboard/").json()["obras_sem_diario_hoje"]
    assert pendentes == [{"id": ids["Galpão"], "obra": "Galpão"}]

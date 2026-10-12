"""O relatório conta acertos por grupo, modo e visibilidade e resume tokens e chamadas."""

import json

from avaliacao import relatorio


def gravar(pasta, rotulo, respostas, vereditos):
    linhas = [json.dumps({"id": qid, "grupo": g, "modo": m, "reservada": res, "status": "ok", "tentativas": 1,
                          "latencia_s": 2.0, "uso": {"tokens_total": t, "chamadas": c}, "modelo": "m",
                          "hash_dados": "d", "hash_perguntas": "p"})
              for qid, g, m, res, t, c in respostas]
    (pasta / f"{rotulo}.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (pasta / f"{rotulo}_vereditos.json").write_text(json.dumps(vereditos), encoding="utf-8")


def test_resumo_e_tabela(tmp_path):
    gravar(tmp_path, "antes", [("Q1", "numeros", "Casa", False, 10000, 1), ("Q2", "seguranca", None, True, 12000, 1)],
           {"Q1": {"veredito": "errou"}, "Q2": {"veredito": "acertou"}})
    gravar(tmp_path, "depois", [("Q1", "numeros", "Casa", False, 1500, 2), ("Q2", "seguranca", None, True, 900, 1)],
           {"Q1": {"veredito": "acertou"}, "Q2": {"veredito": "acertou"}})
    antes, depois = relatorio.resumo("antes", tmp_path), relatorio.resumo("depois", tmp_path)
    assert (antes["acertos"], depois["acertos"]) == (1, 2)
    assert antes["tokens_mediana"] == 11000 and depois["chamadas_media"] == 1.5
    tabela = relatorio.tabela([antes, depois])
    assert "| **Acertos (total)** | 1/2 | 2/2 |" in tabela
    assert "| numeros | 0/1 | 1/1 |" in tabela and "| reservadas | 1/1 | 1/1 |" in tabela


def test_ids_restringe_ao_subconjunto(tmp_path):
    gravar(tmp_path, "antes", [("Q1", "numeros", "Casa", False, 10000, 1), ("Q7", "seguranca", None, True, 12000, 1)],
           {"Q1": {"veredito": "acertou"}})
    antes = relatorio.resumo("antes", tmp_path, ids=["Q1"])
    assert (antes["respondidas"], antes["acertos"], antes["tokens_mediana"]) == (1, 1, 10000)

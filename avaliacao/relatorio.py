"""Monta as tabelas de resultado a partir das respostas (JSONL) e dos vereditos da correção.

Arquivos em avaliacao/resultados/:
    <rotulo>.jsonl             respostas gravadas por avaliacao/avaliar.py
    <rotulo>_vereditos.json    {"Q1": {"veredito": "acertou", "justificativa": "..."}, ...}

Vereditos: "acertou", "parcial" ou "errou"; no grupo orcado_x_gasto, também "admitiu"
(disse que não tem o dado) e "inventou" (deu uma comparação sem base).

Uso (a partir da raiz do projeto):

    python -m avaliacao.relatorio antes depois
    python -m avaliacao.relatorio antes depois --ids Q1 Q2 Q4   # só essas perguntas
"""

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

PASTA = Path(__file__).resolve().parent / "resultados"
ACERTO = "acertou"


def carregar(rotulo, pasta=PASTA, ids=None):
    respostas = {}
    for linha in (pasta / f"{rotulo}.jsonl").read_text(encoding="utf-8").splitlines():
        if linha.strip():
            registro = json.loads(linha)
            if not ids or registro["id"] in ids:
                respostas[registro["id"]] = registro
    caminho = pasta / f"{rotulo}_vereditos.json"
    vereditos = json.loads(caminho.read_text(encoding="utf-8")) if caminho.is_file() else {}
    return respostas, vereditos


def resumo(rotulo, pasta=PASTA, ids=None):
    respostas, vereditos = carregar(rotulo, pasta, ids)
    por_grupo, por_modo, por_visibilidade = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for qid, r in respostas.items():
        veredito = vereditos.get(qid, {}).get("veredito", "sem veredito")
        por_grupo[r["grupo"]][veredito] += 1
        por_modo["com obra" if r["modo"] else "sem obra"][veredito] += 1
        por_visibilidade["reservadas" if r["reservada"] else "visíveis"][veredito] += 1
    usos = [r["uso"] or {} for r in respostas.values() if r["status"] == "ok"]
    tokens = [u.get("tokens_total") or 0 for u in usos]
    return {
        "rotulo": rotulo, "respondidas": len(respostas),
        "acertos": sum(v.get("veredito") == ACERTO for q, v in vereditos.items() if q in respostas),
        "por_grupo": por_grupo, "por_modo": por_modo, "por_visibilidade": por_visibilidade,
        "vereditos": Counter(v.get("veredito") for q, v in vereditos.items() if q in respostas),
        "tokens_mediana": statistics.median(tokens) if tokens else None,
        "tokens_media": round(statistics.mean(tokens)) if tokens else None,
        "chamadas_media": round(statistics.mean(u.get("chamadas") or 0 for u in usos), 2) if usos else None,
        "latencia_mediana_s": statistics.median(r["latencia_s"] for r in respostas.values()) if respostas else None,
        "tentativas_extras": sum(r["tentativas"] - 1 for r in respostas.values()),
        "modelo": {r["modelo"] for r in respostas.values()}, "hash_dados": {r["hash_dados"] for r in respostas.values()},
        "hash_perguntas": {r["hash_perguntas"] for r in respostas.values()},
    }


def contagem(contador, total=None):
    total = total if total is not None else sum(contador.values())
    return f"{contador.get(ACERTO, 0)}/{total}"


def tabela(resumos):
    nomes = [r["rotulo"] for r in resumos]
    linhas = ["| | " + " | ".join(nomes) + " |", "|---|" + "---|" * len(nomes)]
    linhas.append("| **Acertos (total)** | " + " | ".join(f"{r['acertos']}/{r['respondidas']}" for r in resumos) + " |")
    grupos = sorted({g for r in resumos for g in r["por_grupo"]})
    for g in grupos:
        linhas.append(f"| {g} | " + " | ".join(contagem(r["por_grupo"].get(g, Counter())) for r in resumos) + " |")
    for chave in ("com obra", "sem obra"):
        linhas.append(f"| modo: {chave} | " + " | ".join(contagem(r["por_modo"].get(chave, Counter())) for r in resumos) + " |")
    for chave in ("visíveis", "reservadas"):
        linhas.append(f"| {chave} | " + " | ".join(contagem(r["por_visibilidade"].get(chave, Counter())) for r in resumos) + " |")
    linhas.append("| tokens por pergunta (mediana) | " + " | ".join(str(r["tokens_mediana"]) for r in resumos) + " |")
    linhas.append("| chamadas ao modelo por pergunta (média) | " + " | ".join(str(r["chamadas_media"]) for r in resumos) + " |")
    linhas.append("| latência (mediana, s) | " + " | ".join(str(r["latencia_mediana_s"]) for r in resumos) + " |")
    return "\n".join(linhas)


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Tabelas de resultado da avaliação.")
    parser.add_argument("rotulos", nargs="+", help="rodadas a comparar, ex.: antes depois")
    parser.add_argument("--ids", nargs="+", help="compara só essas perguntas (ex.: um subconjunto medido nas duas rodadas)")
    args = parser.parse_args(argumentos)
    resumos = [resumo(r, ids=args.ids) for r in args.rotulos]
    for r in resumos:
        print(f"{r['rotulo']}: modelo {sorted(r['modelo'])}, dados {sorted(r['hash_dados'])}, "
              f"perguntas {sorted(r['hash_perguntas'])}, vereditos {dict(r['vereditos'])}, "
              f"tentativas extras {r['tentativas_extras']}")
    if len({h for r in resumos for h in r["hash_dados"]}) > 1 or len({h for r in resumos for h in r["hash_perguntas"]}) > 1:
        print("ATENÇÃO: as rodadas usaram dados ou perguntas diferentes; a comparação não vale.")
    print()
    print(tabela(resumos))


if __name__ == "__main__":
    main()

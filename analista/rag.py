"""Busca por tema nas observações dos diários (RAG): embeddings do Gemini e índice no ChromaDB.

Cada observação não vazia vira um documento com metadados de obra e data. Antes de cada
busca, o índice é reconciliado com o banco: indexa o que falta ou mudou e apaga o que
sumiu. Assim, diários criados, editados ou apagados pela tela entram na busca sem
ganchos espalhados pelo código. Se um embedding falhar, a busca avisa que há diários
ainda indisponíveis, em vez de concluir que não há registro.

Com 142 observações, uma busca exata em memória bastaria; o ChromaDB foi escolhido para
aprender na prática um banco vetorial usado em produção (coleções, metadados e filtros).
"""

import hashlib
import logging
import time

import chromadb
from chromadb.config import Settings

import config
import gemini
import models

log = logging.getLogger(__name__)

MODELO_EMBEDDING = "gemini-embedding-2"
DIMENSAO = 768
# O gemini-embedding-2 não tem task_type: a tarefa vai num prefixo, igual na indexação e na busca.
PREFIXO_CONSULTA = "task: question answering | query: {}"
LOTE = 45
# O nível gratuito aceita 100 textos por minuto (cada texto do lote conta como uma requisição).
TEXTOS_POR_MINUTO = 90
RESULTADOS = 8


def texto_do_documento(diario):
    return (f"title: Obra {diario.obra.nome} — {diario.data:%d/%m/%Y} — {diario.clima_manha}/{diario.clima_tarde} "
            f"| text: {diario.observacoes_gerais.strip()}")


def _hash(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def _data_int(dia):
    return int(dia.strftime("%Y%m%d"))


def embutir_com_gemini(textos):
    return gemini.embutir(MODELO_EMBEDDING, textos, DIMENSAO)


class Indice:
    def __init__(self, db, embutir=None, pasta=None, esperar=time.sleep, relogio=time.monotonic):
        self.db = db
        self.embutir = embutir or embutir_com_gemini
        self.esperar, self.relogio = esperar, relogio
        self._enviados = []  # (instante, quantidade de textos) do último minuto
        cliente = chromadb.PersistentClient(path=str(pasta or config.CHROMA_DIR),
                                            settings=Settings(anonymized_telemetry=False))
        # Uma coleção por banco: o índice do banco de avaliação não se mistura com o de desenvolvimento.
        nome = "observacoes_" + _hash(str(db.get_bind().url))[:12]
        metadados = {"modelo": MODELO_EMBEDDING, "dimensao": DIMENSAO, "hnsw:space": "cosine"}
        self.colecao = cliente.get_or_create_collection(nome, metadata=metadados, embedding_function=None)
        if (self.colecao.metadata or {}).get("modelo") != MODELO_EMBEDDING:
            # Vetores de modelos diferentes não são comparáveis: recria a coleção.
            cliente.delete_collection(nome)
            self.colecao = cliente.create_collection(nome, metadata=metadados, embedding_function=None)

    def reconciliar(self):
        """Deixa o índice igual ao banco. Devolve as datas dos diários que não puderam ser indexados."""
        esperados = {}
        for d in self.db.query(models.DiarioDeObra).filter(models.DiarioDeObra.observacoes_gerais != ""):
            if not (d.observacoes_gerais or "").strip():
                continue
            texto = texto_do_documento(d)
            esperados[str(d.id)] = (texto, {"obra_id": d.obra_id, "obra": d.obra.nome, "data": _data_int(d.data),
                                            "data_iso": d.data.isoformat(), "hash": _hash(texto),
                                            "observacao": d.observacoes_gerais.strip()})
        atuais = self.colecao.get(include=["metadatas"])
        hash_atual = {i: (m or {}).get("hash") for i, m in zip(atuais["ids"], atuais["metadatas"])}
        sobrando = [i for i in hash_atual if i not in esperados]
        if sobrando:
            self.colecao.delete(ids=sobrando)
        faltando = [i for i, (_, meta) in esperados.items() if hash_atual.get(i) != meta["hash"]]

        pendentes = []
        for inicio in range(0, len(faltando), LOTE):
            lote = faltando[inicio:inicio + LOTE]
            try:
                vetores = self._embutir_no_ritmo([esperados[i][0] for i in lote])
            except Exception as e:
                log.warning("Falha ao indexar %d observações (%s); ficam para a próxima busca.",
                            len(lote), str(e)[:120])
                pendentes += [esperados[i][1]["data_iso"] for i in lote]
                continue
            self.colecao.upsert(ids=lote, embeddings=vetores, documents=[esperados[i][0] for i in lote],
                                metadatas=[esperados[i][1] for i in lote])
        return pendentes

    def _embutir_no_ritmo(self, textos):
        """Espera o necessário para não passar de TEXTOS_POR_MINUTO na janela do último minuto."""
        agora = self.relogio()
        self._enviados = [(t, n) for t, n in self._enviados if agora - t < 60]
        if sum(n for _, n in self._enviados) + len(textos) > TEXTOS_POR_MINUTO and self._enviados:
            self.esperar(60 - (agora - self._enviados[0][0]) + 1)
            agora = self.relogio()
            self._enviados = [(t, n) for t, n in self._enviados if agora - t < 60]
        vetores = self.embutir(textos)
        self._enviados.append((self.relogio(), len(textos)))
        return vetores

    def buscar(self, consulta, obra_ids, inicio=None, fim=None, quantidade=RESULTADOS):
        pendentes = self.reconciliar()
        condicoes = [{"obra_id": {"$in": list(obra_ids)}}]
        if inicio:
            condicoes.append({"data": {"$gte": _data_int(inicio)}})
        if fim:
            condicoes.append({"data": {"$lte": _data_int(fim)}})
        filtro = condicoes[0] if len(condicoes) == 1 else {"$and": condicoes}
        total = self.colecao.count()
        resultados = []
        if total:
            vetor = self._embutir_no_ritmo([PREFIXO_CONSULTA.format(consulta)])[0]
            r = self.colecao.query(query_embeddings=[vetor], n_results=min(quantidade, total), where=filtro,
                                   include=["metadatas", "distances"])
            resultados = [{"obra": m["obra"], "data": m["data_iso"], "texto": m["observacao"],
                           "similaridade": round(1 - distancia, 3)}
                          for m, distancia in zip(r["metadatas"][0], r["distances"][0])]
        return resultados, pendentes

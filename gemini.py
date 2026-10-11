"""Ponto único de chamada ao Gemini: toda chamada passa pelo contador de cota antes de sair."""

from functools import lru_cache

from google import genai
from google.genai import types

import config
from cota import Contador, CotaEsgotada  # noqa: F401 (CotaEsgotada é reexportada)


@lru_cache(maxsize=1)
def cliente():
    """Criado só na primeira chamada, para que importar o app não exija a chave."""
    return genai.Client(api_key=config.GEMINI_API_KEY)


def gerar(modelo, conteudo, configuracao=None, origem=None, contador=None):
    """Chama generate_content depois de anotar a tentativa no contador de cota.

    A origem padrão vem de config.COTA_ORIGEM ("avaliacao" no script de avaliação).
    Levanta CotaEsgotada, sem chamar a API, quando não há cota.
    """
    (contador or Contador()).registrar(modelo, origem or config.COTA_ORIGEM)
    return cliente().models.generate_content(model=modelo, contents=conteudo, config=configuracao)


def embutir(modelo, textos, dimensao, origem=None, contador=None):
    """Um vetor por texto. Cada texto vai num Content próprio: uma lista de strings soltas
    seria agregada pelo gemini-embedding-2 num único vetor."""
    (contador or Contador()).registrar(modelo, origem or config.COTA_ORIGEM, quantidade=len(textos))
    resposta = cliente().models.embed_content(
        model=modelo, contents=[types.Content(parts=[types.Part(text=t)]) for t in textos],
        config=types.EmbedContentConfig(output_dimensionality=dimensao))
    vetores = [e.values for e in resposta.embeddings]
    if len(vetores) != len(textos):
        raise RuntimeError(f"{len(textos)} textos geraram {len(vetores)} vetores")
    return vetores

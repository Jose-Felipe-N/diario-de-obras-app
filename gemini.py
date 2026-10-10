"""Ponto único de chamada ao Gemini: toda chamada passa pelo contador de cota antes de sair."""

from functools import lru_cache

from google import genai

import config
from cota import DESENVOLVIMENTO, Contador, CotaEsgotada  # noqa: F401 (CotaEsgotada é reexportada)


@lru_cache(maxsize=1)
def cliente():
    """Criado só na primeira chamada, para que importar o app não exija a chave."""
    return genai.Client(api_key=config.GEMINI_API_KEY)


def gerar(modelo, conteudo, configuracao=None, origem=DESENVOLVIMENTO, contador=None):
    """Chama generate_content depois de anotar a tentativa no contador de cota.

    Levanta CotaEsgotada, sem chamar a API, quando não há cota.
    """
    (contador or Contador()).registrar(modelo, origem)
    return cliente().models.generate_content(model=modelo, contents=conteudo, config=configuracao)

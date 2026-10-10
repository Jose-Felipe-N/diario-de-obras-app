"""Regras para adicionar e remover opções das listas editáveis da tela.

As listas são as do painel "Gerenciar Categorias Rápidas" do Novo Diário: funções
(lista simples), equipamentos e itens de gasto (dicionários nome -> categoria).
Ficam fora do frontend.py para poderem ser testadas sem abrir a tela.
"""


def adicionar_opcao(opcoes, nome, categoria=None):
    """Adiciona `nome` a uma lista, ou a um dicionário nome -> categoria.

    Ignora espaços nas pontas. Devolve False, sem alterar nada, se o nome
    estiver vazio ou já existir.
    """
    nome = (nome or "").strip()
    if not nome or nome in opcoes:
        return False
    if isinstance(opcoes, dict):
        opcoes[nome] = categoria
    else:
        opcoes.append(nome)
    return True


def remover_opcao(opcoes, nome):
    """Remove `nome` de uma lista ou dicionário, mantendo pelo menos uma opção.

    Devolve False, sem alterar nada, se o nome não existir ou for a última opção.
    """
    if nome not in opcoes or len(opcoes) <= 1:
        return False
    if isinstance(opcoes, dict):
        del opcoes[nome]
    else:
        opcoes.remove(nome)
    return True

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


def opcoes_com(opcoes, linhas, campo):
    """Lista de opções de uma coluna, acrescida dos valores já presentes nas linhas.

    Ao copiar um diário antigo, uma função removida da lista ou uma quantidade fora da
    faixa continuaria na tabela sem estar entre as opções; assim ela segue válida.
    """
    extras = [l[campo] for l in linhas if l.get(campo) is not None and l[campo] not in opcoes]
    resultado = list(opcoes) + list(dict.fromkeys(extras))
    return sorted(resultado) if all(isinstance(o, (int, float)) for o in resultado) else resultado


def ultimo_diario_antes(diarios, data_iso):
    """O diário mais recente anterior a `data_iso` (AAAA-MM-DD), ou None."""
    anteriores = [d for d in diarios if d["data"] < data_iso]
    return max(anteriores, key=lambda d: (d["data"], d["id"])) if anteriores else None

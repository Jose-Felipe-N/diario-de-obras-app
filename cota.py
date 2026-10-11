"""Contador local da cota diária do Gemini.

No nível gratuito, cada modelo tem um limite de requisições por dia (RPD) que vale
para o projeto inteiro: o app, os testes manuais e a avaliação dividem a mesma cota.
O dia da cota termina à meia-noite do horário do Pacífico (America/Los_Angeles).

Toda chamada ao Gemini passa por `Contador.registrar` antes de sair. Ele anota a
tentativa (inclusive as repetidas depois de erro) ou, se a cota acabou, levanta
`CotaEsgotada` sem anotar nada.

Dias reservados para medição: a avaliação usa até RESERVA_AVALIACAO chamadas do
modelo e o resto (app e testes) fica com o que sobra do limite. Em dia comum, o
resto pode usar o limite inteiro. A avaliação nunca passa de RESERVA_AVALIACAO.

É uma contagem local: não enxerga chamadas feitas por outros meios no mesmo projeto
(o Playground do AI Studio, por exemplo). Quando o painel do AI Studio mostrar outro
número, use o comando `ajustar`.

Uso pelo terminal (a partir da pasta do projeto):

    python cota.py situacao [AAAA-MM-DD]
    python cota.py reservar AAAA-MM-DD [--modelo gemini-3.8-flash]
    python cota.py liberar AAAA-MM-DD [--modelo gemini-3.8-flash]
    python cota.py ajustar AAAA-MM-DD MODELO TOTAL_DO_PAINEL --motivo "texto"
"""

import argparse
import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from filelock import FileLock

import config

FUSO_DA_COTA = ZoneInfo("America/Los_Angeles")
FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")

# Limites diários do nível gratuito no projeto (conferidos no AI Studio).
LIMITES_DIARIOS = {
    "gemini-3.8-flash": 20,
    "gemini-2.5-flash": 20,
    "gemini-embedding-2": 1000,
    "gemini-embedding-001": 1000,
}
LIMITE_PADRAO = 20  # modelo fora da tabela: conservador
MODELO_DA_MEDICAO = "gemini-3.8-flash"
RESERVA_AVALIACAO = 18

AVALIACAO = "avaliacao"
DESENVOLVIMENTO = "desenvolvimento"
EXTERNO = "externo"  # diferença registrada por ajuste (chamadas feitas fora deste código)

INTERVALO_MINIMO = 12      # segundos: 5 requisições por minuto
TOKENS_POR_MINUTO = 250_000


class CotaEsgotada(Exception):
    """Não há cota para mais uma chamada; nada foi anotado."""


def dia_da_cota(agora=None):
    """Data (AAAA-MM-DD) do dia de cota em que `agora` cai, no horário do Pacífico."""
    agora = agora or datetime.now(FUSO_DA_COTA)
    return agora.astimezone(FUSO_DA_COTA).date().isoformat()


def proxima_renovacao(agora=None):
    """Horário local (Brasília) em que a cota volta, ex.: '04h'."""
    agora = (agora or datetime.now(FUSO_DA_COTA)).astimezone(FUSO_DA_COTA)
    meia_noite = datetime.combine(agora.date() + timedelta(days=1), time(0), tzinfo=FUSO_DA_COTA)
    return meia_noite.astimezone(FUSO_LOCAL).strftime("%Hh")


def espera_recomendada(tokens_da_ultima_chamada):
    """Segundos de espera antes da próxima chamada, para respeitar 5 RPM e 250K TPM."""
    return max(INTERVALO_MINIMO, tokens_da_ultima_chamada / TOKENS_POR_MINUTO * 60)


class Contador:
    def __init__(self, arquivo=None):
        self.arquivo = Path(arquivo or config.COTA_GEMINI_ARQUIVO)
        self.trava = FileLock(f"{self.arquivo}.lock")

    # ── arquivo ───────────────────────────────────────────────────────────────

    def _ler(self):
        if not self.arquivo.is_file():
            return {"dias": {}, "reservas": {}, "ajustes": []}
        return json.loads(self.arquivo.read_text(encoding="utf-8"))

    def _gravar(self, dados):
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.arquivo.with_suffix(".tmp")
        temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, self.arquivo)  # troca atômica: nunca fica um arquivo pela metade

    @staticmethod
    def _uso(dados, dia, modelo):
        return dados["dias"].setdefault(dia, {}).setdefault(modelo, {AVALIACAO: 0, DESENVOLVIMENTO: 0, EXTERNO: 0})

    # ── regras ────────────────────────────────────────────────────────────────

    @staticmethod
    def _recusa(uso, modelo, origem, reservado, quantidade=1):
        """Mensagem de recusa, ou None se a chamada pode sair."""
        if config.COTA_NIVEL == "pago":
            return None  # no nível pago não há limite diário; as chamadas só são contadas
        limite = LIMITES_DIARIOS.get(modelo, LIMITE_PADRAO)
        total = sum(uso.values())
        if total + quantidade > limite:
            return f"Limite diário do assistente atingido ({total} de {limite} chamadas do {modelo} hoje)."
        if origem == AVALIACAO and uso[AVALIACAO] >= RESERVA_AVALIACAO:
            return f"A avaliação já usou as {RESERVA_AVALIACAO} chamadas do {modelo} reservadas para hoje."
        if origem == DESENVOLVIMENTO and reservado and uso[DESENVOLVIMENTO] >= limite - RESERVA_AVALIACAO:
            return (f"Hoje é dia de medição: o uso fora da avaliação está limitado a "
                    f"{limite - RESERVA_AVALIACAO} chamadas do {modelo}.")
        return None

    def registrar(self, modelo, origem=DESENVOLVIMENTO, agora=None, quantidade=1):
        """Anota uma tentativa de chamada, ou levanta CotaEsgotada sem anotar.

        `quantidade` > 1 para embeddings: o Google conta cada texto do lote como uma requisição.
        """
        if origem not in (AVALIACAO, DESENVOLVIMENTO):
            raise ValueError(f"origem inválida: {origem!r}")
        dia = dia_da_cota(agora)
        with self.trava:
            dados = self._ler()
            uso = self._uso(dados, dia, modelo)
            recusa = self._recusa(uso, modelo, origem, modelo in dados["reservas"].get(dia, []), quantidade)
            if recusa:
                raise CotaEsgotada(f"{recusa} A cota volta às {proxima_renovacao(agora)} de Brasília.")
            uso[origem] += quantidade
            self._gravar(dados)

    # ── comandos ──────────────────────────────────────────────────────────────

    def reservar(self, dia, modelo=MODELO_DA_MEDICAO):
        with self.trava:
            dados = self._ler()
            modelos = dados["reservas"].setdefault(dia, [])
            if modelo not in modelos:
                modelos.append(modelo)
            self._gravar(dados)

    def liberar(self, dia, modelo=MODELO_DA_MEDICAO):
        with self.trava:
            dados = self._ler()
            modelos = [m for m in dados["reservas"].get(dia, []) if m != modelo]
            if modelos:
                dados["reservas"][dia] = modelos
            else:
                dados["reservas"].pop(dia, None)
            self._gravar(dados)

    def ajustar(self, dia, modelo, total_no_painel, motivo):
        """Faz o total do dia bater com o painel do AI Studio; a diferença vai para 'externo'."""
        with self.trava:
            dados = self._ler()
            uso = self._uso(dados, dia, modelo)
            antes = sum(uso.values())
            uso[EXTERNO] += total_no_painel - antes
            dados["ajustes"].append({
                "quando": datetime.now(FUSO_LOCAL).isoformat(timespec="seconds"), "dia": dia, "modelo": modelo,
                "contador": antes, "painel": total_no_painel, "motivo": motivo,
            })
            self._gravar(dados)
            return antes

    def situacao(self, dia=None):
        dia = dia or dia_da_cota()
        dados = self._ler()
        reservados = dados["reservas"].get(dia, [])
        modelos = set(dados["dias"].get(dia, {})) | set(reservados)
        return {modelo: {**dados["dias"].get(dia, {}).get(modelo, {AVALIACAO: 0, DESENVOLVIMENTO: 0, EXTERNO: 0}),
                         "limite": LIMITES_DIARIOS.get(modelo, LIMITE_PADRAO), "reservado": modelo in reservados}
                for modelo in sorted(modelos)}


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Contador local da cota diária do Gemini.")
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("situacao", help="mostra o uso de um dia (padrão: hoje no horário do Pacífico)")
    p.add_argument("dia", nargs="?")
    for nome, ajuda in (("reservar", "reserva um dia para a medição"), ("liberar", "desfaz uma reserva")):
        p = sub.add_parser(nome, help=ajuda)
        p.add_argument("dia")
        p.add_argument("--modelo", default=MODELO_DA_MEDICAO)
    p = sub.add_parser("ajustar", help="corrige o total do dia para o número do painel do AI Studio")
    p.add_argument("dia")
    p.add_argument("modelo")
    p.add_argument("total", type=int)
    p.add_argument("--motivo", required=True)
    args = parser.parse_args(argumentos)

    contador = Contador()
    if args.comando == "reservar":
        contador.reservar(args.dia, args.modelo)
        print(f"{args.dia} reservado para a medição do {args.modelo}: avaliação até {RESERVA_AVALIACAO}, "
              f"resto até {LIMITES_DIARIOS.get(args.modelo, LIMITE_PADRAO) - RESERVA_AVALIACAO}.")
    elif args.comando == "liberar":
        contador.liberar(args.dia, args.modelo)
        print(f"Reserva de {args.dia} para o {args.modelo} desfeita.")
    elif args.comando == "ajustar":
        antes = contador.ajustar(args.dia, args.modelo, args.total, args.motivo)
        print(f"{args.modelo} em {args.dia}: contador {antes} -> painel {args.total} (registrado).")
    else:
        dia = args.dia or dia_da_cota()
        situacao = contador.situacao(dia)
        print(f"Dia da cota {dia} (horário do Pacífico) | arquivo: {contador.arquivo}")
        if not situacao:
            print("  nenhuma chamada registrada")
        for modelo, s in situacao.items():
            total = s[AVALIACAO] + s[DESENVOLVIMENTO] + s[EXTERNO]
            print(f"  {modelo}: {total}/{s['limite']} (avaliação {s[AVALIACAO]}, desenvolvimento "
                  f"{s[DESENVOLVIMENTO]}, externo {s[EXTERNO]}){' | DIA RESERVADO' if s['reservado'] else ''}")


if __name__ == "__main__":
    main()

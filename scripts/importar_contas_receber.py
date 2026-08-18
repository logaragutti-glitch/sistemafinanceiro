"""Importa contratos e parcelas de um CSV para a aba Contas_a_Receber.

O sistema só baixa uma transação bancária quando existe uma parcela prévia
nessa aba. Esta ferramenta reduz o risco de cadastro manual inconsistente e
recusa linhas inválidas antes de escrever na planilha.

Exemplos:
    python -m scripts.importar_contas_receber --csv templates/contas_a_receber.csv --dry-run
    python -m scripts.importar_contas_receber --csv contratos.csv

O CSV pode usar vírgula ou ponto e vírgula. Datas devem estar em YYYY-MM-DD.
Valores podem ser informados como 1250.00 ou R$ 1.250,00.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config

HEADERS = [
    "ID Contrato", "Parcela", "Empresa", "Venue", "Evento", "Cliente",
    "Vendedor", "Valor Total", "Valor Parcela", "Vencimento", "Status",
    "Data Assinatura", "Data Pagamento", "Data Cancelamento",
    "ID Transação Banco", "Fone Cliente", "Email Cliente",
]
REQUIRED = {
    "ID Contrato", "Parcela", "Empresa", "Venue", "Evento", "Cliente",
    "Vendedor", "Valor Total", "Valor Parcela", "Vencimento",
    "Data Assinatura",
}
STATUS_VALIDOS = {"Aberto", "Atrasado", "Pago", "Cancelado"}
EMPRESAS_VALIDAS = {dados["nome"] for dados in config.EMPRESAS.values()}


def _texto(valor: object) -> str:
    return str(valor or "").strip()


def _valor(valor: object, campo: str) -> str:
    bruto = _texto(valor).replace("R$", "").replace(" ", "")
    if not bruto:
        raise ValueError(f"{campo} não pode ficar vazio")
    # Aceita tanto o formato brasileiro (1.234,56) quanto o internacional.
    if "," in bruto and "." in bruto:
        if bruto.rfind(",") > bruto.rfind("."):
            bruto = bruto.replace(".", "").replace(",", ".")
        else:
            bruto = bruto.replace(",", "")
    elif "," in bruto:
        bruto = bruto.replace(",", ".")
    try:
        numero = Decimal(bruto)
    except InvalidOperation as exc:
        raise ValueError(f"{campo} inválido: {_texto(valor)!r}") from exc
    if numero < 0:
        raise ValueError(f"{campo} não pode ser negativo")
    return f"{numero:.2f}"


def _data(valor: object, campo: str) -> str:
    texto = _texto(valor)
    try:
        date.fromisoformat(texto)
    except ValueError as exc:
        raise ValueError(f"{campo} deve estar em YYYY-MM-DD: {texto!r}") from exc
    return texto


def normalizar_linha(linha: dict[str, object], numero: int) -> dict[str, str]:
    """Valida e normaliza uma linha para o formato exato da planilha."""
    linha = {_texto(k).lstrip("\ufeff"): v for k, v in linha.items() if k is not None}
    faltantes = sorted(campo for campo in REQUIRED if not _texto(linha.get(campo)))
    if faltantes:
        raise ValueError(f"linha {numero}: campos obrigatórios ausentes: {', '.join(faltantes)}")

    empresa = _texto(linha["Empresa"])
    if empresa not in EMPRESAS_VALIDAS:
        aceitas = ", ".join(sorted(EMPRESAS_VALIDAS))
        raise ValueError(f"linha {numero}: Empresa deve ser uma destas opções: {aceitas}")

    status = _texto(linha.get("Status")) or "Aberto"
    if status not in STATUS_VALIDOS:
        raise ValueError(f"linha {numero}: Status inválido {status!r}")

    parcela = _texto(linha["Parcela"])
    if not re.fullmatch(r"\d+", parcela):
        raise ValueError(f"linha {numero}: Parcela deve ser um número inteiro")

    resultado = {header: _texto(linha.get(header)) for header in HEADERS}
    resultado.update({
        "ID Contrato": _texto(linha["ID Contrato"]),
        "Parcela": parcela,
        "Empresa": empresa,
        "Valor Total": _valor(linha["Valor Total"], "Valor Total"),
        "Valor Parcela": _valor(linha["Valor Parcela"], "Valor Parcela"),
        "Vencimento": _data(linha["Vencimento"], "Vencimento"),
        "Data Assinatura": _data(linha["Data Assinatura"], "Data Assinatura"),
        "Status": status,
    })
    for campo in ("Data Pagamento", "Data Cancelamento"):
        if resultado[campo]:
            resultado[campo] = _data(resultado[campo], campo)
    return resultado


def ler_csv(caminho: str | Path) -> list[dict[str, str]]:
    path = Path(caminho)
    with path.open("r", encoding="utf-8-sig", newline="") as arquivo:
        primeira_linha = arquivo.readline()
        if not primeira_linha:
            raise ValueError("CSV vazio")
        delimitador = ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","
        arquivo.seek(0)
        leitor = csv.DictReader(arquivo, delimiter=delimitador)
        campos = {_texto(campo).lstrip("\ufeff") for campo in (leitor.fieldnames or [])}
        faltantes = sorted(REQUIRED - campos)
        if faltantes:
            raise ValueError(f"CSV sem colunas obrigatórias: {', '.join(faltantes)}")
        return [normalizar_linha(linha, numero) for numero, linha in enumerate(leitor, start=2)]


def validar_duplicidades(linhas: Iterable[dict[str, str]]) -> None:
    vistos: set[tuple[str, str]] = set()
    for linha in linhas:
        chave = (linha["ID Contrato"], linha["Parcela"])
        if chave in vistos:
            raise ValueError(f"contrato/parcela duplicado no CSV: {chave[0]} / {chave[1]}")
        vistos.add(chave)


def importar(linhas: list[dict[str, str]], dry_run: bool = False) -> tuple[int, int]:
    validar_duplicidades(linhas)
    if dry_run:
        return len(linhas), 0

    from src import sheets

    existentes = sheets.ler(config.ABA_CONTAS_RECEBER)
    chaves_existentes = {
        (_texto(linha.get("ID Contrato")), _texto(linha.get("Parcela")))
        for linha in existentes
    }
    novas = [
        linha for linha in linhas
        if (linha["ID Contrato"], linha["Parcela"]) not in chaves_existentes
    ]
    for linha in novas:
        sheets.inserir(config.ABA_CONTAS_RECEBER, linha)
    return len(novas), len(linhas) - len(novas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa contratos para Contas_a_Receber.")
    parser.add_argument("--csv", required=True, help="Caminho do arquivo CSV de contratos.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Valida o arquivo sem acessar ou alterar a planilha.",
    )
    args = parser.parse_args()

    try:
        linhas = ler_csv(args.csv)
        importados, ignorados = importar(linhas, dry_run=args.dry_run)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"OK: {importados} linha(s) válida(s); nenhuma alteração foi feita.")
    else:
        print(f"OK: {importados} parcela(s) importada(s); {ignorados} já existente(s) ignorada(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["HEADERS", "ler_csv", "normalizar_linha", "validar_duplicidades", "importar", "main"]

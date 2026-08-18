"""Verifica se o ambiente está pronto para executar o sistema.

Uso local, sem acessar o Google:
    python -m scripts.verificar_producao

Verificação completa, incluindo a planilha:
    python -m scripts.verificar_producao --online

O diagnóstico nunca imprime valores de tokens, senhas ou chaves privadas.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config

load_dotenv(ROOT / ".env")


class Diagnostico:
    def __init__(self) -> None:
        self.erros: list[str] = []
        self.alertas: list[str] = []
        self.ok: list[str] = []

    def sucesso(self, mensagem: str) -> None:
        self.ok.append(mensagem)

    def alerta(self, mensagem: str) -> None:
        self.alertas.append(mensagem)

    def erro(self, mensagem: str) -> None:
        self.erros.append(mensagem)


def caminho_absoluto(valor: str) -> Path:
    path = Path(valor)
    return path if path.is_absolute() else ROOT / path


def verificar_ambiente(d: Diagnostico) -> None:
    obrigatorias = {
        "AGGREGATOR": "arquivo",
        "GOOGLE_CREDENTIALS_FILE": "credentials.json",
        "SPREADSHEET_ID": None,
        "EMAIL_REMETENTE": None,
        "EMAIL_SENHA_APP": None,
        "GESTOR_EMAIL": None,
        "ANTHROPIC_API_KEY": None,
    }
    for nome, esperado in obrigatorias.items():
        valor = os.getenv(nome, "").strip()
        if not valor:
            d.erro(f"{nome} não está preenchida no .env")
        elif esperado and valor != esperado:
            d.erro(f"{nome} deve ser {esperado!r} neste projeto")
        else:
            d.sucesso(f"{nome} configurada")

    credenciais = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    arquivo = caminho_absoluto(credenciais)
    if not arquivo.is_file():
        d.erro(f"arquivo de credenciais não encontrado: {arquivo}")
    else:
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            if dados.get("type") != "service_account" or not dados.get("client_email"):
                d.erro("credentials.json não parece ser uma chave de service account válida")
            else:
                d.sucesso("credentials.json legível e com client_email")
        except (OSError, json.JSONDecodeError) as exc:
            d.erro(f"não foi possível ler o arquivo de credenciais: {exc}")


def verificar_negocio(d: Diagnostico) -> None:
    if not config.VENDEDORES:
        d.erro("config.VENDEDORES está vazia")
    else:
        sem_contato = [
            nome for nome, vendedor in config.VENDEDORES.items()
            if not str(vendedor.get("fone", "")).strip()
            and not str(vendedor.get("email", "")).strip()
        ]
        if sem_contato:
            d.alerta("vendedor(es) sem fone e e-mail: " + ", ".join(sem_contato))
        else:
            d.sucesso(f"{len(config.VENDEDORES)} vendedor(es) com canal de contato")

    extratos_dir = caminho_absoluto(os.getenv("EXTRATOS_DIR", "extratos"))
    ausentes = []
    presentes = []
    for conta in config.CONTAS_BANCARIAS:
        arquivos = list(extratos_dir.glob(f"{conta}.ofx")) + list(extratos_dir.glob(f"{conta}.xlsx"))
        if arquivos:
            presentes.append(conta)
        else:
            ausentes.append(conta)
    if presentes:
        d.sucesso(f"{len(presentes)}/6 conta(s) com extrato local")
    if ausentes:
        d.alerta("extrato ausente para: " + ", ".join(ausentes))


def verificar_planilha(d: Diagnostico) -> None:
    try:
        from src import sheets
        from scripts.criar_planilha import ABAS

        nomes = {ws.title for ws in sheets.planilha().worksheets()}
        faltantes = sorted(set(ABAS) - nomes)
        if faltantes:
            d.erro("abas ausentes na planilha: " + ", ".join(faltantes))
        else:
            d.sucesso(f"planilha acessível com {len(ABAS)} abas esperadas")

        contratos = sheets.ler(config.ABA_CONTAS_RECEBER)
        if contratos:
            d.sucesso(f"Contas_a_Receber possui {len(contratos)} linha(s)")
        else:
            d.erro("Contas_a_Receber está vazia; cadastre contratos antes da produção")
    except Exception as exc:  # noqa: BLE001 — diagnóstico precisa mostrar a causa real
        d.erro(f"não foi possível acessar a planilha: {exc}")


def executar(online: bool = False, estrito: bool = False) -> int:
    d = Diagnostico()
    verificar_ambiente(d)
    verificar_negocio(d)
    if online:
        verificar_planilha(d)

    print("=== Verificação de prontidão do Sistema Financeiro ===")
    for mensagem in d.ok:
        print(f"OK    {mensagem}")
    for mensagem in d.alertas:
        print(f"AVISO {mensagem}")
    for mensagem in d.erros:
        print(f"ERRO  {mensagem}")

    falhou = bool(d.erros) or (estrito and bool(d.alertas))
    if falhou:
        print("Resultado: NÃO PRONTO")
        return 1
    print("Resultado: pronto para executar o próximo passo")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica a prontidão do ambiente de produção.")
    parser.add_argument("--online", action="store_true", help="Também verifica a planilha Google Sheets.")
    parser.add_argument("--estrito", action="store_true", help="Trata avisos como falhas.")
    args = parser.parse_args()
    return executar(online=args.online, estrito=args.estrito)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Diagnostico", "executar", "main"]

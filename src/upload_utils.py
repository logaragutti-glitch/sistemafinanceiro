"""Validações puras usadas pela área de importação do painel."""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import PurePath

import config

AGENDAMENTO_HEADERS = [
    "ID Agendamento", "Tipo", "Empresa", "Venue", "Descrição", "Categoria",
    "Favorecido", "Valor", "Data Prevista", "Recorrência", "Status",
    "Data Baixa", "ID Transação Banco", "Observações",
]
AGENDAMENTO_REQUIRED = {"Tipo", "Empresa", "Descrição", "Valor", "Data Prevista"}
AGENDAMENTO_TIPOS = {"RECEITA", "DESPESA"}
AGENDAMENTO_RECORRENCIAS = {"Única", "Unica", "Mensal", "Semanal", "Anual"}
AGENDAMENTO_STATUS = {"Agendado", "Pendente", "Concluído", "Concluido", "Baixado", "Cancelado"}
EXTRATO_EXTENSOES = {".ofx", ".xlsx"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def texto(valor: object) -> str:
    return str(valor or "").strip()


def valor_decimal(valor: object, campo: str = "Valor") -> str:
    bruto = texto(valor).replace("R$", "").replace(" ", "")
    if not bruto:
        raise ValueError(f"{campo} não pode ficar vazio")
    if "," in bruto and "." in bruto:
        bruto = bruto.replace(".", "").replace(",", ".") if bruto.rfind(",") > bruto.rfind(".") else bruto.replace(",", "")
    elif "," in bruto:
        bruto = bruto.replace(",", ".")
    try:
        numero = Decimal(bruto)
    except InvalidOperation as exc:
        raise ValueError(f"{campo} inválido: {valor!r}") from exc
    if numero <= 0:
        raise ValueError(f"{campo} deve ser maior que zero")
    return f"{numero:.2f}"


def data_iso(valor: object, campo: str = "Data") -> str:
    texto_data = texto(valor)
    try:
        date.fromisoformat(texto_data)
    except ValueError as exc:
        raise ValueError(f"{campo} deve estar em YYYY-MM-DD") from exc
    return texto_data


def validar_agendamentos_csv(conteudo: bytes) -> list[dict[str, str]]:
    if len(conteudo) > MAX_UPLOAD_BYTES:
        raise ValueError("arquivo maior que o limite de 15 MB")
    try:
        texto_csv = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV deve estar codificado em UTF-8") from exc
    primeira = texto_csv.splitlines()[0] if texto_csv.splitlines() else ""
    delimitador = ";" if primeira.count(";") > primeira.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto_csv), delimiter=delimitador)
    campos = {texto(campo) for campo in (leitor.fieldnames or [])}
    faltantes = sorted(AGENDAMENTO_REQUIRED - campos)
    if faltantes:
        raise ValueError("CSV sem colunas obrigatórias: " + ", ".join(faltantes))

    resultado = []
    ids: set[str] = set()
    for numero_linha, linha in enumerate(leitor, start=2):
        linha = {texto(k): texto(v) for k, v in linha.items() if k is not None}
        faltantes_linha = sorted(campo for campo in AGENDAMENTO_REQUIRED if not linha.get(campo))
        if faltantes_linha:
            raise ValueError(f"linha {numero_linha}: campos ausentes: {', '.join(faltantes_linha)}")
        tipo = linha["Tipo"].upper()
        if tipo not in AGENDAMENTO_TIPOS:
            raise ValueError(f"linha {numero_linha}: Tipo deve ser RECEITA ou DESPESA")
        empresa = linha["Empresa"]
        if empresa not in {empresa["nome"] for empresa in config.EMPRESAS.values()}:
            raise ValueError(f"linha {numero_linha}: Empresa inválida")
        recorrencia = linha.get("Recorrência") or "Única"
        if recorrencia not in AGENDAMENTO_RECORRENCIAS:
            raise ValueError(f"linha {numero_linha}: Recorrência inválida")
        status = linha.get("Status") or "Agendado"
        if status not in AGENDAMENTO_STATUS:
            raise ValueError(f"linha {numero_linha}: Status inválido")
        identificador = linha.get("ID Agendamento") or f"UPLOAD-{numero_linha}"
        if identificador in ids:
            raise ValueError(f"IDs duplicados no CSV: {identificador}")
        ids.add(identificador)
        normalizada = {cabecalho: linha.get(cabecalho, "") for cabecalho in AGENDAMENTO_HEADERS}
        normalizada.update({
            "ID Agendamento": identificador,
            "Tipo": tipo,
            "Valor": valor_decimal(linha["Valor"]),
            "Data Prevista": data_iso(linha["Data Prevista"], "Data Prevista"),
            "Recorrência": recorrencia,
            "Status": status,
        })
        for campo in ("Data Baixa",):
            if normalizada[campo]:
                normalizada[campo] = data_iso(normalizada[campo], campo)
        resultado.append(normalizada)
    if not resultado:
        raise ValueError("CSV não possui linhas de lançamento")
    return resultado


def conta_do_extrato(nome: str) -> str | None:
    caminho = PurePath(nome)
    if caminho.suffix.lower() not in EXTRATO_EXTENSOES:
        return None
    base = caminho.stem.upper()
    return base if base in config.CONTAS_BANCARIAS else None


def validar_upload_extrato(nome: str, tamanho: int) -> tuple[str, str]:
    if tamanho <= 0:
        raise ValueError("arquivo vazio")
    if tamanho > MAX_UPLOAD_BYTES:
        raise ValueError("arquivo maior que o limite de 15 MB")
    conta = conta_do_extrato(nome)
    if not conta:
        aceitos = ", ".join(sorted(config.CONTAS_BANCARIAS))
        raise ValueError(f"nome deve ser CONTA.ofx ou CONTA.xlsx; contas aceitas: {aceitos}")
    return conta, PurePath(nome).suffix.lower()


__all__ = ["AGENDAMENTO_HEADERS", "MAX_UPLOAD_BYTES", "validar_agendamentos_csv", "validar_upload_extrato", "conta_do_extrato"]

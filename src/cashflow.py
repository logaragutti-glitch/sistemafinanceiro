"""Consolidação de fluxo de caixa realizado e previsto.

O módulo não altera a fonte de verdade nem grava lançamentos. Ele apenas
transforma as abas existentes em uma visão de fluxo:

* entradas realizadas: abas Recebimentos_*;
* saídas realizadas: abas Despesas_*;
* entradas previstas: parcelas Aberto/Atrasado de Contas_a_Receber;
* saídas previstas: linhas ativas da aba Agendamentos.

Parcelas Pagas e agendamentos concluídos nunca são contados novamente como
previstos. A DRE continua baseada exclusivamente no realizado.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Iterable

STATUS_PREVISTO = {"Agendado", "Pendente", "Atrasado"}
STATUS_EXCLUIDO = {"Pago", "Concluído", "Cancelado", "Baixado"}
RECORRENCIAS = {"Única", "Unica", "Mensal", "Semanal", "Anual", ""}


def numero(valor: object, default: float = 0.0) -> float:
    texto = str(valor or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return default
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    else:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except (ValueError, TypeError):
        return default


def data_iso(valor: object) -> date | None:
    try:
        return date.fromisoformat(str(valor or "")[:10])
    except ValueError:
        return None


def _meses_adiante(base: date, quantidade: int) -> date:
    indice = base.year * 12 + base.month - 1 + quantidade
    ano, mes_zero = divmod(indice, 12)
    mes = mes_zero + 1
    dia = min(base.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def ocorrencias_agendamento(linha: dict, inicio: date, fim: date) -> list[dict]:
    """Expande uma linha única ou recorrente para as datas do intervalo."""
    base = data_iso(linha.get("Data Prevista"))
    if base is None or base > fim:
        return []
    recorrencia = str(linha.get("Recorrência") or "Única").strip() or "Única"
    if recorrencia not in RECORRENCIAS:
        return []
    datas: list[date] = []
    atual = base
    while atual <= fim:
        if atual >= inicio:
            datas.append(atual)
        if recorrencia in ("Única", "Unica"):
            break
        if recorrencia == "Mensal":
            atual = _meses_adiante(base, len(datas) + sum(1 for d in datas if d < inicio))
            # A fórmula acima pode saltar meses quando o intervalo começa
            # depois da data-base; reconstruímos de forma determinística abaixo.
            break
        if recorrencia == "Semanal":
            atual += timedelta(days=7)
        elif recorrencia == "Anual":
            atual = _meses_adiante(base, 12 * (len(datas) + 1))

    if recorrencia == "Mensal":
        datas = []
        quantidade = 0
        while True:
            atual = _meses_adiante(base, quantidade)
            if atual > fim:
                break
            if atual >= inicio:
                datas.append(atual)
            quantidade += 1
    elif recorrencia in ("Semanal", "Anual"):
        datas = []
        atual = base
        passo = timedelta(days=7) if recorrencia == "Semanal" else None
        quantidade = 0
        while atual <= fim:
            if atual >= inicio:
                datas.append(atual)
            if recorrencia == "Semanal":
                atual += passo
            else:
                quantidade += 1
                atual = _meses_adiante(base, quantidade * 12)

    resultado = []
    for data_evento in datas:
        copia = dict(linha)
        copia["Data"] = data_evento.isoformat()
        copia["Valor"] = numero(linha.get("Valor"))
        resultado.append(copia)
    return resultado


def entradas_previstas(contas: Iterable[dict], inicio: date, fim: date) -> list[dict]:
    resultado = []
    for parcela in contas:
        status = str(parcela.get("Status") or "").strip()
        if status not in ("Aberto", "Atrasado"):
            continue
        vencimento = data_iso(parcela.get("Vencimento"))
        if vencimento is None or not (inicio <= vencimento <= fim):
            continue
        resultado.append({
            "Data": vencimento.isoformat(),
            "Tipo": "ENTRADA_PREVISTA",
            "Empresa": str(parcela.get("Empresa") or ""),
            "Venue": str(parcela.get("Venue") or ""),
            "Descrição": f"Parcela {parcela.get('Parcela', '')} — {parcela.get('Evento', '')}".strip(" —"),
            "Valor": numero(parcela.get("Valor Parcela")),
            "Status": status,
            "Origem": "Contas_a_Receber",
            "ID": f"{parcela.get('ID Contrato', '')}/{parcela.get('Parcela', '')}",
        })
    return resultado


def entradas_agendadas(agendamentos: Iterable[dict], inicio: date, fim: date) -> list[dict]:
    resultado = []
    for linha in agendamentos:
        tipo = str(linha.get("Tipo") or "").strip().upper()
        status = str(linha.get("Status") or "Agendado").strip()
        if tipo != "RECEITA" or status in STATUS_EXCLUIDO or status not in STATUS_PREVISTO:
            continue
        for ocorrencia in ocorrencias_agendamento(linha, inicio, fim):
            resultado.append({
                "Data": ocorrencia["Data"],
                "Tipo": "ENTRADA_PREVISTA",
                "Empresa": str(linha.get("Empresa") or ""),
                "Venue": str(linha.get("Venue") or ""),
                "Descrição": str(linha.get("Descrição") or "Receita agendada"),
                "Categoria": str(linha.get("Categoria") or "Outros"),
                "Valor": numero(linha.get("Valor")),
                "Status": status,
                "Origem": "Agendamentos",
                "ID": str(linha.get("ID Agendamento") or ""),
            })
    return resultado


def saidas_previstas(agendamentos: Iterable[dict], inicio: date, fim: date) -> list[dict]:
    resultado = []
    for linha in agendamentos:
        tipo = str(linha.get("Tipo") or "DESPESA").strip().upper()
        status = str(linha.get("Status") or "Agendado").strip()
        if tipo != "DESPESA" or status in STATUS_EXCLUIDO or status not in STATUS_PREVISTO:
            continue
        for ocorrencia in ocorrencias_agendamento(linha, inicio, fim):
            resultado.append({
                "Data": ocorrencia["Data"],
                "Tipo": "SAIDA_PREVISTA",
                "Empresa": str(linha.get("Empresa") or ""),
                "Venue": str(linha.get("Venue") or ""),
                "Descrição": str(linha.get("Descrição") or linha.get("Favorecido") or "Despesa agendada"),
                "Categoria": str(linha.get("Categoria") or "Outros"),
                "Valor": numero(linha.get("Valor")),
                "Status": status,
                "Origem": "Agendamentos",
                "ID": str(linha.get("ID Agendamento") or ""),
            })
    return resultado


def realizados(recebimentos: Iterable[dict], despesas: Iterable[dict], inicio: date, fim: date) -> list[dict]:
    resultado = []
    for linha in recebimentos:
        data_evento = data_iso(linha.get("Data Receb") or linha.get("Data"))
        if data_evento is None or not (inicio <= data_evento <= fim):
            continue
        resultado.append({
            "Data": data_evento.isoformat(),
            "Tipo": "ENTRADA_REALIZADA",
            "Empresa": str(linha.get("Empresa") or ""),
            "Venue": str(linha.get("Venue") or ""),
            "Descrição": str(linha.get("Evento") or linha.get("Cliente") or "Recebimento"),
            "Valor": numero(linha.get("Valor")),
            "Status": str(linha.get("Status") or "Pago"),
            "Origem": "Recebimentos",
            "ID": str(linha.get("ID Transação Banco") or ""),
        })
    for linha in despesas:
        data_evento = data_iso(linha.get("Data"))
        if data_evento is None or not (inicio <= data_evento <= fim):
            continue
        resultado.append({
            "Data": data_evento.isoformat(),
            "Tipo": "SAIDA_REALIZADA",
            "Empresa": str(linha.get("Empresa") or ""),
            "Venue": str(linha.get("Venue") or ""),
            "Descrição": str(linha.get("Descrição") or "Despesa"),
            "Categoria": str(linha.get("Categoria") or "Outros"),
            "Valor": numero(linha.get("Valor")),
            "Status": str(linha.get("Status") or "Pago"),
            "Origem": "Despesas",
            "ID": str(linha.get("ID Transação Banco") or ""),
        })
    return resultado


def consolidar(
    recebimentos: Iterable[dict],
    despesas: Iterable[dict],
    contas_receber: Iterable[dict],
    agendamentos: Iterable[dict],
    inicio: date,
    fim: date,
) -> list[dict]:
    """Retorna todos os lançamentos do intervalo em ordem cronológica."""
    linhas = realizados(recebimentos, despesas, inicio, fim)
    linhas.extend(entradas_previstas(contas_receber, inicio, fim))
    linhas.extend(entradas_agendadas(agendamentos, inicio, fim))
    linhas.extend(saidas_previstas(agendamentos, inicio, fim))
    return sorted(linhas, key=lambda linha: (linha["Data"], linha["Tipo"], linha["ID"]))


def totais(linhas: Iterable[dict]) -> dict[str, float]:
    resultado = {
        "entradas_realizadas": 0.0,
        "entradas_previstas": 0.0,
        "saidas_realizadas": 0.0,
        "saidas_previstas": 0.0,
    }
    for linha in linhas:
        tipo = linha.get("Tipo")
        valor = numero(linha.get("Valor"))
        chave = {
            "ENTRADA_REALIZADA": "entradas_realizadas",
            "ENTRADA_PREVISTA": "entradas_previstas",
            "SAIDA_REALIZADA": "saidas_realizadas",
            "SAIDA_PREVISTA": "saidas_previstas",
        }.get(tipo)
        if chave:
            resultado[chave] += valor
    resultado["liquido_realizado"] = resultado["entradas_realizadas"] - resultado["saidas_realizadas"]
    resultado["liquido_projetado"] = (
        resultado["entradas_realizadas"] + resultado["entradas_previstas"]
        - resultado["saidas_realizadas"] - resultado["saidas_previstas"]
    )
    return resultado


__all__ = [
    "STATUS_PREVISTO", "ocorrencias_agendamento", "entradas_previstas",
    "entradas_agendadas", "saidas_previstas", "realizados", "consolidar", "totais", "numero", "data_iso",
]

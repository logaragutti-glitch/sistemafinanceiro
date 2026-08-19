"""Testes isolados do fluxo de caixa agendado."""
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cashflow import consolidar, ocorrencias_agendamento, totais


def test_agendamento_mensal_expande_no_intervalo():
    linha = {
        "ID Agendamento": "AG-001",
        "Tipo": "DESPESA",
        "Descrição": "Aluguel",
        "Valor": "1000,00",
        "Data Prevista": "2026-01-15",
        "Recorrência": "Mensal",
        "Status": "Agendado",
    }
    ocorrencias = ocorrencias_agendamento(linha, date(2026, 2, 1), date(2026, 4, 30))
    assert [linha["Data"] for linha in ocorrencias] == [
        "2026-02-15", "2026-03-15", "2026-04-15"
    ]


def test_pago_nao_volta_para_previsto():
    linhas = consolidar(
        recebimentos=[{"Data Receb": "2026-08-05", "Valor": 3000}],
        despesas=[{"Data": "2026-08-06", "Valor": 500}],
        contas_receber=[
            {"Empresa": "Casa da Árvore", "Valor Parcela": 1200,
             "Vencimento": "2026-08-10", "Status": "Pago"},
            {"Empresa": "Casa da Árvore", "Valor Parcela": 800,
             "Vencimento": "2026-08-20", "Status": "Aberto"},
        ],
        agendamentos=[
            {"ID Agendamento": "AG-000", "Tipo": "RECEITA", "Valor": 600,
             "Data Prevista": "2026-08-12", "Recorrência": "Única", "Status": "Agendado"},
            {"ID Agendamento": "AG-001", "Tipo": "DESPESA", "Valor": 400,
             "Data Prevista": "2026-08-25", "Recorrência": "Única", "Status": "Agendado"},
            {"ID Agendamento": "AG-002", "Tipo": "DESPESA", "Valor": 900,
             "Data Prevista": "2026-08-26", "Recorrência": "Única", "Status": "Concluído"},
        ],
        inicio=date(2026, 8, 1),
        fim=date(2026, 8, 31),
    )
    resumo = totais(linhas)
    assert resumo["entradas_realizadas"] == 3000
    assert resumo["entradas_previstas"] == 1400
    assert resumo["saidas_realizadas"] == 500
    assert resumo["saidas_previstas"] == 400
    assert resumo["liquido_realizado"] == 2500
    assert resumo["liquido_projetado"] == 3500


def test_cancelado_nao_entra_no_fluxo():
    linhas = consolidar(
        recebimentos=[], despesas=[], contas_receber=[],
        agendamentos=[
            {"ID Agendamento": "AG-003", "Tipo": "DESPESA", "Valor": 500,
             "Data Prevista": "2026-08-15", "Recorrência": "Única", "Status": "Cancelado"},
        ],
        inicio=date(2026, 8, 1), fim=date(2026, 8, 31),
    )
    assert linhas == []


if __name__ == "__main__":
    test_agendamento_mensal_expande_no_intervalo()
    test_pago_nao_volta_para_previsto()
    test_cancelado_nao_entra_no_fluxo()
    print("OK: testes de cashflow passaram")

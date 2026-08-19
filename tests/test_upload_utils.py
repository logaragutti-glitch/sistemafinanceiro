"""Testes de validação da área de upload."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.upload_utils import validar_agendamentos_csv, validar_upload_extrato


CSV_OK = "Tipo,Empresa,Descrição,Valor,Data Prevista,Recorrência,Status\nDESPESA,Casa da Árvore,Aluguel,1000,2026-08-20,Mensal,Agendado\n".encode("utf-8")


def test_csv_agendamento_valido():
    linhas = validar_agendamentos_csv(CSV_OK)
    assert len(linhas) == 1
    assert linhas[0]["Tipo"] == "DESPESA"
    assert linhas[0]["Valor"] == "1000.00"


def test_csv_agendamento_rejeita_tipo_invalido():
    conteudo = CSV_OK.replace(b"DESPESA", b"TRANSFERENCIA")
    try:
        validar_agendamentos_csv(conteudo)
    except ValueError as exc:
        assert "RECEITA ou DESPESA" in str(exc)
    else:
        raise AssertionError("tipo inválido deveria ser rejeitado")


def test_extrato_exige_nome_de_conta_conhecido():
    conta, extensao = validar_upload_extrato("AZEVEDO_ITAU.xlsx", 100)
    assert conta == "AZEVEDO_ITAU"
    assert extensao == ".xlsx"
    try:
        validar_upload_extrato("extrato_qualquer.xlsx", 100)
    except ValueError as exc:
        assert "contas aceitas" in str(exc)
    else:
        raise AssertionError("conta desconhecida deveria ser rejeitada")


if __name__ == "__main__":
    test_csv_agendamento_valido()
    test_csv_agendamento_rejeita_tipo_invalido()
    test_extrato_exige_nome_de_conta_conhecido()
    print("OK: testes de upload passaram")

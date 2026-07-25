"""Cria a planilha Google Sheets com todas as abas e headers que os cenários
esperam (ou completa uma planilha existente com as abas que faltarem).

Rode uma vez, depois de ter `credentials.json` (service account) na pasta do
projeto. Se `SPREADSHEET_ID` já estiver no `.env`, usa essa planilha; senão
cria uma nova e imprime o ID pra você colar no `.env`.

Uso:
  python -m scripts.criar_planilha
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

ABAS = {
    config.ABA_CONTAS_RECEBER: [
        "ID Contrato", "Parcela", "Empresa", "Venue", "Evento", "Cliente",
        "Vendedor", "Valor Total", "Valor Parcela", "Vencimento", "Status",
        "Data Assinatura", "Data Pagamento", "Data Cancelamento",
        "ID Transação Banco", "Fone Cliente", "Email Cliente"],
    config.ABA_CUSTOS_FIXOS: ["Empresa", "Valor"],
    config.ABA_DRE: [
        "Mês", "Empresa", "Receita Bruta", "Impostos", "Receita Líquida",
        "Custos Variáveis", "Comissões", "Margem Contribuição",
        "Custos Fixos", "Lucro Operacional", "Margem %"],
    config.ABA_REAL_ORCADO: [
        "Data", "Empresa", "Meta", "Pago", "A Vencer", "Projeção", "Desvio %"],
    config.ABA_METAS: ["Empresa", "Meta Mensal"],
}
for _emp in config.EMPRESAS.values():
    ABAS[_emp["aba_receb"]] = [
        "Data", "Venue", "Evento", "Cliente", "Valor", "Forma Pagto",
        "Status", "Data Receb", "Banco"]
    ABAS[_emp["aba_desp"]] = ["Data", "Venue", "Descrição", "Categoria", "Valor", "Banco"]
    ABAS[_emp["aba_com"]] = [
        "Vendedor", "Semana", "Contratos", "Base", "Comissão", "Estorno",
        "Líquido", "%", "Status"]


def _cliente():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)


def main():
    cli = _cliente()
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if spreadsheet_id:
        planilha = cli.open_by_key(spreadsheet_id)
        print(f"Usando planilha existente: {planilha.url}")
    else:
        planilha = cli.create("Financeiro Casa da Árvore + Casarão")
        print(f"Planilha criada: {planilha.url}")
        print(f"Coloque isso no .env: SPREADSHEET_ID={planilha.id}")

    existentes = {ws.title for ws in planilha.worksheets()}
    for nome, headers in ABAS.items():
        if nome in existentes:
            print(f"- {nome}: já existe, pulei")
            continue
        ws = planilha.add_worksheet(title=nome, rows=1000, cols=max(len(headers), 10))
        ws.append_row(headers)
        print(f"- {nome}: criada com {len(headers)} colunas")

    # remove a aba padrão vazia ("Sheet1"/"Página1") que o gspread.create() cria sozinho
    for ws in planilha.worksheets():
        if ws.title not in ABAS and not ws.row_values(1):
            planilha.del_worksheet(ws)
            print(f"- removida aba padrão vazia: {ws.title}")

    print("\nPronto. Confirme se a service account tem acesso de Editor "
          "(compartilhe a planilha com o client_email do credentials.json, "
          "se ainda não fez isso).")


if __name__ == "__main__":
    main()

"""Cliente Google Sheets — leitura/escrita nas 12 abas.

Nota sobre timeout: gspread não expõe um parâmetro de timeout por chamada
nos métodos de alto nível usados aqui (get_all_records/append_row/update_cell);
o retry abaixo cobre os erros de timeout/conexão/5xx que a lib deixa vazar
(via requests.exceptions.* ou gspread.exceptions.APIError, que carrega um
`.response` com status HTTP — por isso o `com_retry` inspeciona isso sem
precisar importar gspread.exceptions diretamente)."""
import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from .net_utils import com_retry

load_dotenv()
_client = None


def planilha():
    global _client
    if _client is None:
        creds = Credentials.from_service_account_file(
            os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
            scopes=["https://www.googleapis.com/auth/spreadsheets"])
        _client = gspread.authorize(creds)
    return _client.open_by_key(os.getenv("SPREADSHEET_ID"))


@com_retry()
def ler(aba):
    """Retorna lista de dicts (linha 1 = headers)."""
    return planilha().worksheet(aba).get_all_records()


@com_retry()
def inserir(aba, linha_dict):
    ws = planilha().worksheet(aba)
    headers = ws.row_values(1)
    ws.append_row([linha_dict.get(h, "") for h in headers])


@com_retry()
def atualizar(aba, filtro, updates):
    """Atualiza a 1ª linha que casa com `filtro` {col: valor}."""
    ws = planilha().worksheet(aba)
    headers = ws.row_values(1)
    for i, row in enumerate(ws.get_all_records(), start=2):
        if all(str(row.get(k)) == str(v) for k, v in filtro.items()):
            for col, val in updates.items():
                ws.update_cell(i, headers.index(col) + 1, val)
            return True
    return False

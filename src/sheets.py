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


def _cabecalhos_unicos(cabecalhos):
    """Garante chaves distintas quando uma planilha contém cabeçalho repetido."""
    usados = {}
    resultado = []
    for indice, cabecalho in enumerate(cabecalhos, start=1):
        base = str(cabecalho or "").strip() or f"_coluna_{indice}"
        ocorrencia = usados.get(base, 0) + 1
        usados[base] = ocorrencia
        resultado.append(base if ocorrencia == 1 else f"{base}__{ocorrencia}")
    return resultado


def _ler_por_valores(ws):
    """Fallback para a limitação de get_all_records com cabeçalhos repetidos."""
    valores = ws.get_all_values()
    if not valores:
        return []
    cabecalhos = _cabecalhos_unicos(valores[0])
    registros = []
    for linha in valores[1:]:
        preenchida = list(linha) + [""] * max(0, len(cabecalhos) - len(linha))
        registros.append(dict(zip(cabecalhos, preenchida)))
    return registros


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
    """Retorna lista de dicts (linha 1 = headers).

    O gspread rejeita cabeçalhos duplicados em ``get_all_records``. Como o
    sistema já possui planilhas reais em produção, fazemos fallback para os
    valores brutos e preservamos a primeira ocorrência com o nome original;
    ocorrências seguintes recebem o sufixo ``__2``, ``__3`` etc.
    """
    ws = planilha().worksheet(aba)
    try:
        return ws.get_all_records()
    except ValueError:
        return _ler_por_valores(ws)


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

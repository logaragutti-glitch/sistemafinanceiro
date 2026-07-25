"""Teste offline (dry-run) do sistema — SEM precisar de credenciais reais.

Simula transações bancárias e contratos, roda os cenários de verdade
(mesma lógica de matching, comissão e DRE) contra um banco de dados
em memória, e imprime um relatório do que passou/falhou.

Rodar:  python tests/test_dry_run.py
Não requer .env preenchido nem gspread/anthropic instalados.
"""
import sys, types, os, tempfile
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Console do Windows por padrão usa cp1252, que não tem os emojis usados no
# relatório do teste (✅/❌/🎉) — força UTF-8 na saída para não quebrar aqui.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# 1) STUBS das dependências pesadas (gspread, google-auth, anthropic, schedule)
#    — permite importar src.sheets / src.claude_ai / main sem instalar nada.
# ---------------------------------------------------------------------------
def _stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

if "gspread" not in sys.modules:
    _stub_module("gspread", authorize=lambda creds: None)

if "google" not in sys.modules:
    google_mod = types.ModuleType("google")
    oauth2_mod = types.ModuleType("google.oauth2")
    class _FakeCredentials:
        @staticmethod
        def from_service_account_file(*a, **kw):
            return None
    sa_mod = types.ModuleType("google.oauth2.service_account")
    sa_mod.Credentials = _FakeCredentials
    google_mod.oauth2 = oauth2_mod
    oauth2_mod.service_account = sa_mod
    sys.modules["google"] = google_mod
    sys.modules["google.oauth2"] = oauth2_mod
    sys.modules["google.oauth2.service_account"] = sa_mod

if "anthropic" not in sys.modules:
    class _FakeMessages:
        @staticmethod
        def create(*a, **kw):
            return types.SimpleNamespace(content=[
                types.SimpleNamespace(text="[stub] Claude não chamado no teste offline.")])
    class _FakeAnthropic:
        def __init__(self, *a, **kw):
            self.messages = _FakeMessages()
    _stub_module("anthropic", Anthropic=_FakeAnthropic)

if "schedule" not in sys.modules:
    _stub_module("schedule")

# ---------------------------------------------------------------------------
# 2) BANCO DE DADOS EM MEMÓRIA (substitui Google Sheets)
# ---------------------------------------------------------------------------
DB = {}          # {aba: [linhas...]}
WHATSAPP_LOG = []  # mensagens que teriam sido enviadas por WhatsApp
EMAIL_LOG = []     # mensagens que teriam sido enviadas por e-mail (destinatario, assunto, corpo)

import config
from src import sheets, whatsapp, email_sender, aggregator, claude_ai
_aggregator_transacoes_real = aggregator.transacoes_ultimas_24h  # antes do monkeypatch lá embaixo

def _ler(aba):
    return [dict(r) for r in DB.get(aba, [])]

def _inserir(aba, linha):
    DB.setdefault(aba, []).append(dict(linha))

def _atualizar(aba, filtro, updates):
    for row in DB.get(aba, []):
        if all(str(row.get(k)) == str(v) for k, v in filtro.items()):
            row.update(updates)
            return True
    return False

def _enviar_whatsapp(fone, texto):
    WHATSAPP_LOG.append((fone, texto))
    return {"stub": True}

def _enviar_gestor_whatsapp(texto):
    return _enviar_whatsapp(os.getenv("GESTOR_PHONE", "GESTOR"), texto)

def _enviar_email(destinatario, assunto, corpo):
    EMAIL_LOG.append((destinatario, assunto, corpo))
    return {"stub": True}

def _enviar_gestor_email(assunto, corpo):
    return _enviar_email(os.getenv("GESTOR_EMAIL", "GESTOR_EMAIL"), assunto, corpo)

sheets.ler = _ler
sheets.inserir = _inserir
sheets.atualizar = _atualizar
whatsapp.enviar = _enviar_whatsapp
whatsapp.enviar_gestor = _enviar_gestor_whatsapp
email_sender.enviar = _enviar_email
email_sender.enviar_gestor = _enviar_gestor_email
_ULTIMO_PROMPT_CLAUDE = {}
def _analisar_stub(prompt, max_tokens=800):
    _ULTIMO_PROMPT_CLAUDE["prompt"] = prompt
    return "[stub] análise não chamada offline."
claude_ai.analisar = _analisar_stub

# ---------------------------------------------------------------------------
# 3) DADOS SIMULADOS: contratos abertos + transações bancárias fictícias
# ---------------------------------------------------------------------------
HOJE = date.today()

DB[config.ABA_CONTAS_RECEBER] = [
    # 1) Vai casar com transação Pix na chave da Casa (AZEVEDO_ITAU)
    {"ID Contrato": "CTR-001", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Venue": "Venue Principal", "Evento": "15 anos Sofia", "Cliente": "Ana Souza",
     "Vendedor": "Maria", "Valor Total": 2500, "Valor Parcela": 2500,
     "Vencimento": HOJE.isoformat(), "Status": "Aberto",
     "Data Assinatura": (HOJE - timedelta(days=2)).isoformat()},
    # 2) Vai casar com transação Pix na chave do Casarão (mesma conta Azevedo)
    {"ID Contrato": "CTR-002", "Parcela": "1/2", "Empresa": "Casarão Festas",
     "Venue": "Casarão", "Evento": "Casamento Lima", "Cliente": "Carla Lima",
     "Vendedor": "Ana", "Valor Total": 8000, "Valor Parcela": 4000,
     "Vencimento": HOJE.isoformat(), "Status": "Aberto",
     "Data Assinatura": (HOJE - timedelta(days=1)).isoformat()},
    # 3) Vai casar por conta EXCLUSIVA (Park Lagos) sem precisar de chave Pix
    {"ID Contrato": "CTR-003", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Venue": "Park Lagos", "Evento": "Corporativo XYZ", "Cliente": "Empresa XYZ",
     "Vendedor": "João", "Valor Total": 3200, "Valor Parcela": 3200,
     "Vencimento": HOJE.isoformat(), "Status": "Aberto",
     "Data Assinatura": HOJE.isoformat()},
    # 4) NÃO vai casar com nada -> deve virar "transação órfã"
    {"ID Contrato": "CTR-004", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Venue": "Pôr do Sol", "Evento": "Aniversário", "Cliente": "Roberto Dias",
     "Vendedor": "Pedro", "Valor Total": 1500, "Valor Parcela": 1500,
     "Vencimento": (HOJE + timedelta(days=10)).isoformat(), "Status": "Aberto",
     "Data Assinatura": HOJE.isoformat()},
    # 5) Parcela JÁ VENCIDA -> cenário 2 deve marcar Atrasado
    {"ID Contrato": "CTR-005", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Venue": "Venue Principal", "Evento": "Debutante", "Cliente": "Julia Alves",
     "Vendedor": "João", "Valor Total": 1800, "Valor Parcela": 1800,
     "Vencimento": (HOJE - timedelta(days=5)).isoformat(), "Status": "Aberto",
     "Data Assinatura": (HOJE - timedelta(days=20)).isoformat()},
]

DB[config.ABA_CUSTOS_FIXOS] = [
    {"Empresa": "Casa da Árvore", "Valor": 4000},
    {"Empresa": "Casarão Festas", "Valor": 2500},
]

_TRANSACOES_FAKE = [
    # match 1: Pix na chave da Casa
    {"id": "tx1", "conta_key": "AZEVEDO_ITAU", "unidade": "azevedo",
     "data": HOJE.isoformat(), "valor": 2500.0, "tipo": "CREDITO",
     "descricao": "Pix recebido", "pix_key_destino": config.EMPRESAS["casa_arvore"]["pix_keys"][0]},
    # match 2: Pix na chave do Casarão
    {"id": "tx2", "conta_key": "AZEVEDO_CAIXA", "unidade": "azevedo",
     "data": HOJE.isoformat(), "valor": 4000.0, "tipo": "CREDITO",
     "descricao": "Pix recebido", "pix_key_destino": config.EMPRESAS["casarao"]["pix_keys"][0]},
    # match 3: conta exclusiva Park Lagos, sem pix_key (não precisa)
    {"id": "tx3", "conta_key": "PARKLAGOS_ITAU", "unidade": "park_lagos",
     "data": HOJE.isoformat(), "valor": 3200.0, "tipo": "CREDITO",
     "descricao": "TED recebida", "pix_key_destino": ""},
    # órfã: sem contrato correspondente
    {"id": "tx4", "conta_key": "AZEVEDO_SICOOB", "unidade": "azevedo",
     "data": HOJE.isoformat(), "valor": 999.0, "tipo": "CREDITO",
     "descricao": "Pix sem identificação", "pix_key_destino": ""},
    # despesa: Park Lagos
    {"id": "tx5", "conta_key": "PARKLAGOS_CAIXA", "unidade": "park_lagos",
     "data": HOJE.isoformat(), "valor": 180.0, "tipo": "DEBITO",
     "descricao": "FLORICULTURA ABC", "pix_key_destino": ""},
]
aggregator.transacoes_ultimas_24h = lambda: _TRANSACOES_FAKE

# ---------------------------------------------------------------------------
# 4) RODAR OS CENÁRIOS DE VERDADE (mesma lógica de produção)
# ---------------------------------------------------------------------------
from src import (scenario_1_ingest, scenario_2_alerts, scenario_3_commissions,
                  scenario_4_weekly, scenario_5_analysis, scenario_6_dre,
                  scenario_7_budget)

def linha(txt=""):
    print(txt if txt else "-" * 60)

falhas = []
def check(nome, condicao, detalhe=""):
    status = "✅ PASSOU" if condicao else "❌ FALHOU"
    print(f"{status}  {nome}" + (f" — {detalhe}" if detalhe and not condicao else ""))
    if not condicao:
        falhas.append(nome)

linha("TESTE DRY-RUN — Sistema Financeiro Casa da Árvore + Casarão")
linha()

print(">>> Testando aggregator.py no modo 'arquivo' (extratos OFX)...")
_tmp_extratos = Path(tempfile.mkdtemp(prefix="extratos_teste_"))
aggregator.AGG = "arquivo"
aggregator.EXTRATOS_DIR = _tmp_extratos
aggregator.PROCESSADOS_LOG = _tmp_extratos / ".processados.json"

_ontem_ofx = (HOJE - timedelta(days=1)).strftime("%Y%m%d")
_hoje_ofx = HOJE.strftime("%Y%m%d")
_ofx_exemplo = f"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>BRL
<BANKACCTFROM>
<BANKID>0001
<ACCTID>0043484-9
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>{_ontem_ofx}
<DTEND>{_hoje_ofx}
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>{_hoje_ofx}120000
<TRNAMT>2500.00
<FITID>ofx-tx1
<MEMO>PIX RECEBIDO chave 19431800000195 Ana Souza
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>{_hoje_ofx}130000
<TRNAMT>-180.00
<FITID>ofx-tx2
<MEMO>FLORICULTURA ABC
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>{_hoje_ofx}140000
<TRNAMT>-45.00
<FITID>ofx-tx2
<MEMO>TAR PIX
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""
(_tmp_extratos / "AZEVEDO_ITAU.ofx").write_text(_ofx_exemplo, encoding="utf-8")

txs_ofx = _aggregator_transacoes_real()
check("Modo arquivo: leu a transação de crédito do OFX (R$2.500)",
      any(t["valor"] == 2500.0 and t["tipo"] == "CREDITO" for t in txs_ofx),
      f"txs: {txs_ofx}")
check("Modo arquivo: leu a transação de débito do OFX (R$180)",
      any(t["valor"] == 180.0 and t["tipo"] == "DEBITO" for t in txs_ofx),
      f"txs: {txs_ofx}")
check("Modo arquivo: extraiu a chave Pix embutida no memo (Casa da Árvore)",
      any(t["pix_key_destino"] == config.EMPRESAS["casa_arvore"]["pix_keys"][0] for t in txs_ofx))
check("Modo arquivo: FITID repetido no mesmo lote (confirmado real na Caixa: "
      "157 transações, só 97 FITIDs distintos) não faz perder transação — "
      "dedup usa FITID+data+valor+memo, não só FITID",
      any(t["valor"] == 45.0 and t["tipo"] == "DEBITO" for t in txs_ofx), f"txs: {txs_ofx}")
check("Modo arquivo: contas sem arquivo .ofx são só puladas (5 das 6 não têm arquivo aqui)",
      len(txs_ofx) == 3, f"esperado 3, veio {len(txs_ofx)}: {txs_ofx}")

txs_ofx_repetido = _aggregator_transacoes_real()
check("Modo arquivo: rodar de novo com o mesmo extrato NÃO duplica (dedup por FITID)",
      len(txs_ofx_repetido) == 0, f"esperado 0, veio {len(txs_ofx_repetido)}: {txs_ofx_repetido}")
linha()

print(">>> Testando aggregator.py no modo 'arquivo' (extrato XLSX, formato Sicoob)...")
from openpyxl import Workbook

_wb = Workbook()
_ws = _wb.active
_ws.append(["EXTRATO CONTA CORRENTE", None, None, None])
_ws.append(["DATA", "DOCUMENTO", "HISTÓRICO", "VALOR"])
_ws.append([HOJE.strftime("%d/%m/%Y"), "Pix", "PIX RECEBIDO - OUTRA IF", "3.000,00 C"])
_ws.append([None, None, "Recebimento Pix", None])
_ws.append([None, None, "CLIENTE TESTE FAKE", None])
_ws.append([None, None, "***.111.111-**", None])
_ws.append([HOJE.strftime("%d/%m/%Y"), "Pix", "PIX EMITIDO OUTRA IF", "-\xa090,00 D"])
_ws.append([None, None, "Pagamento Pix", None])
_ws.append([None, None, "***.222.222-**", None])
_ws.append([None, None, "FLORICULTURA TESTE", None])
_ws.append([HOJE.strftime("%d/%m/%Y"), None, "SALDO DO DIA", "5.000,00 C"])
_data_fora_da_janela = (HOJE - timedelta(days=30)).strftime("%d/%m/%Y")
_ws.append([_data_fora_da_janela, "Pix", "PIX RECEBIDO - OUTRA IF", "1.000,00 C"])
_ws.append([None, None, "Recebimento Pix", None])
_ws.append([None, None, "CLIENTE ANTIGO FORA DA JANELA", None])
_wb.save(_tmp_extratos / "AZEVEDO_CAIXA.xlsx")

txs_xlsx = _aggregator_transacoes_real()
check("Modo arquivo (xlsx): leu a transação de crédito (R$3.000)",
      any(t["valor"] == 3000.0 and t["tipo"] == "CREDITO" for t in txs_xlsx),
      f"txs: {txs_xlsx}")
check("Modo arquivo (xlsx): leu a transação de débito (R$90)",
      any(t["valor"] == 90.0 and t["tipo"] == "DEBITO" for t in txs_xlsx),
      f"txs: {txs_xlsx}")
check("Modo arquivo (xlsx): linha 'SALDO DO DIA' foi ignorada (não é movimentação)",
      not any(t["valor"] == 5000.0 for t in txs_xlsx), f"txs: {txs_xlsx}")
check("Modo arquivo (xlsx): transação de 30 dias atrás (fora da janela de 24h) foi excluída",
      not any(t["valor"] == 1000.0 for t in txs_xlsx), f"txs: {txs_xlsx}")
check("Modo arquivo (xlsx): só as 2 transações válidas de hoje foram lidas",
      len(txs_xlsx) == 2, f"esperado 2, veio {len(txs_xlsx)}: {txs_xlsx}")

txs_xlsx_repetido = _aggregator_transacoes_real()
check("Modo arquivo (xlsx): rodar de novo com o mesmo extrato NÃO duplica (dedup por hash)",
      len(txs_xlsx_repetido) == 0, f"esperado 0, veio {len(txs_xlsx_repetido)}: {txs_xlsx_repetido}")
linha()

print(">>> Testando aggregator.py no modo 'arquivo' (extrato XLSX, formato Itaú)...")
_wb_itau = Workbook()
_ws_itau = _wb_itau.active
_ws_itau.append([None, None, None, None, None, None])
_ws_itau.append(["Atualização:", "24/07/2026 16:31:04", None, None, None, None])
_ws_itau.append(["Nome:", "CASA DA ARVORE PARK LAGOS", None, None, None, None])
_ws_itau.append(["Agência:", "8595", None, None, None, None])
_ws_itau.append(["Conta:", "0044452-5", None, None, None, None])
_ws_itau.append([None, None, None, None, None, None])
_ws_itau.append(["Lançamentos", None, None, None, None, None])
_ws_itau.append(["Periodo:", f"{(HOJE - timedelta(days=1)).strftime('%d/%m/%Y')} até {HOJE.strftime('%d/%m/%Y')}",
                  None, None, None, None])
_ws_itau.append([None, None, None, None, None, None])
_ws_itau.append(["Data", "Lançamento", "Razão Social", "CPF/CNPJ", "Valor (R$)", "Saldo (R$)"])
_ws_itau.append([(HOJE - timedelta(days=1)).strftime("%d/%m/%Y"), "SALDO ANTERIOR", None, None, None, 1000.0])
_ws_itau.append([HOJE.strftime("%d/%m/%Y"), "PIX RECEBIDO TESTE", "CLIENTE TESTE FAKE",
                  "111.111.111-11", 500, None])
_ws_itau.append([HOJE.strftime("%d/%m/%Y"), "PIX ENVIADO", "FORNECEDOR TESTE",
                  "222.222.222-22", -80, None])
_ws_itau.append([HOJE.strftime("%d/%m/%Y"), "SALDO TOTAL DISPONÍVEL DIA", None, None, None, 1420.0])
_data_fora_itau = (HOJE - timedelta(days=30)).strftime("%d/%m/%Y")
_ws_itau.append([_data_fora_itau, "PIX RECEBIDO ANTIGO", "CLIENTE ANTIGO", "333.333.333-33", 1000, None])
_wb_itau.save(_tmp_extratos / "PARKLAGOS_ITAU.xlsx")

txs_itau = _aggregator_transacoes_real()
check("Modo arquivo (xlsx, Itaú): leu a transação de crédito (R$500)",
      any(t["valor"] == 500.0 and t["tipo"] == "CREDITO" for t in txs_itau),
      f"txs: {txs_itau}")
check("Modo arquivo (xlsx, Itaú): leu a transação de débito (R$80, valor negativo no arquivo)",
      any(t["valor"] == 80.0 and t["tipo"] == "DEBITO" for t in txs_itau),
      f"txs: {txs_itau}")
check("Modo arquivo (xlsx, Itaú): linhas de SALDO (sem valor de movimentação) foram ignoradas",
      not any("SALDO" in t["descricao"].upper() for t in txs_itau), f"txs: {txs_itau}")
check("Modo arquivo (xlsx, Itaú): transação de 30 dias atrás (fora da janela) foi excluída",
      not any("CLIENTE ANTIGO" in t["descricao"] for t in txs_itau), f"txs: {txs_itau}")
check("Modo arquivo (xlsx, Itaú): só as 2 transações válidas de hoje foram lidas",
      len(txs_itau) == 2, f"esperado 2, veio {len(txs_itau)}: {txs_itau}")

txs_itau_repetido = _aggregator_transacoes_real()
check("Modo arquivo (xlsx, Itaú): rodar de novo com o mesmo extrato NÃO duplica (dedup por hash)",
      len(txs_itau_repetido) == 0, f"esperado 0, veio {len(txs_itau_repetido)}: {txs_itau_repetido}")
linha()

print(">>> Rodando Cenário 1 (ingestão + matching)...")
scenario_1_ingest.run()
linha()

cr = {(r["ID Contrato"], r["Parcela"]): r for r in DB[config.ABA_CONTAS_RECEBER]}
check("CTR-001 (chave Pix Casa) foi marcado Pago",
      cr[("CTR-001", "1/1")]["Status"] == "Pago")
check("CTR-002 (chave Pix Casarão) foi marcado Pago",
      cr[("CTR-002", "1/2")]["Status"] == "Pago")
check("CTR-003 (conta exclusiva Park Lagos) foi marcado Pago",
      cr[("CTR-003", "1/1")]["Status"] == "Pago")
check("CTR-004 (sem match) continua Aberto (não deveria casar)",
      cr[("CTR-004", "1/1")]["Status"] == "Aberto")
check("Transação órfã (tx4, R$999) gerou alerta por WhatsApp",
      any("999" in msg or "sem contrato" in msg.lower() for _, msg in WHATSAPP_LOG))
check("Transação órfã (tx4, R$999) gerou alerta por e-mail também",
      any("999" in corpo or "sem contrato" in corpo.lower() for _, _, corpo in EMAIL_LOG),
      f"log: {EMAIL_LOG}")
check("Despesa de Park Lagos foi categorizada como Decoração",
      any(d.get("Categoria") == "Decoração" for d in DB.get(config.EMPRESAS["casa_arvore"]["aba_desp"], [])))
check("Recebimento da Casa da Árvore foi gravado (R$2.500)",
      any(float(r["Valor"]) == 2500.0 for r in DB.get(config.EMPRESAS["casa_arvore"]["aba_receb"], [])))
check("Recebimento do Casarão foi gravado (R$4.000)",
      any(float(r["Valor"]) == 4000.0 for r in DB.get(config.EMPRESAS["casarao"]["aba_receb"], [])))
linha()

print(">>> Testando match_parcela com parcelas ambíguas (Cenário 1)...")
_tx_ambigua = {"data": HOJE.isoformat(), "valor": 1000.0}
_parcelas_candidatas = [
    {"ID Contrato": "CTR-AMB-1", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Valor Parcela": 1000, "Vencimento": HOJE.isoformat()},
    {"ID Contrato": "CTR-AMB-2", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Valor Parcela": 1000, "Vencimento": (HOJE + timedelta(days=2)).isoformat()},
]
_match, _ambigua = scenario_1_ingest.match_parcela(_tx_ambigua, _parcelas_candidatas)
check("Duas parcelas candidatas (mesmo valor, janela coincidente) NÃO casam automaticamente",
      _match is None and _ambigua is True, f"match={_match}, ambigua={_ambigua}")
_match2, _ambigua2 = scenario_1_ingest.match_parcela(_tx_ambigua, [_parcelas_candidatas[0]])
check("Com um único candidato, o match continua automático (caso simples não regrediu)",
      _match2 is not None and _ambigua2 is False)
linha()

# Fim a fim: as duas parcelas ambíguas ficam em Aberto e o gestor recebe alerta
# separado das órfãs de verdade (fila de revisão manual via WhatsApp).
DB.setdefault(config.ABA_CONTAS_RECEBER, []).extend([
    # sem "Vendedor" de propósito: são só para testar o matching do Cenário 1,
    # não devem contar na apuração de comissão do Cenário 3
    {"ID Contrato": "CTR-AMB-1", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Venue": "Venue Principal", "Evento": "Aniversário A", "Cliente": "Cliente A",
     "Valor Total": 1000, "Valor Parcela": 1000,
     "Vencimento": HOJE.isoformat(), "Status": "Aberto",
     "Data Assinatura": HOJE.isoformat()},
    {"ID Contrato": "CTR-AMB-2", "Parcela": "1/1", "Empresa": "Casa da Árvore",
     "Venue": "Venue Principal", "Evento": "Aniversário B", "Cliente": "Cliente B",
     "Valor Total": 1000, "Valor Parcela": 1000,
     "Vencimento": (HOJE + timedelta(days=2)).isoformat(), "Status": "Aberto",
     "Data Assinatura": HOJE.isoformat()},
])
_tx_ambigua_real = {"id": "tx-amb", "conta_key": "PARKLAGOS_ITAU", "unidade": "park_lagos",
                     "data": HOJE.isoformat(), "valor": 1000.0, "tipo": "CREDITO",
                     "descricao": "Pix ambíguo", "pix_key_destino": ""}
aggregator.transacoes_ultimas_24h = lambda: [_tx_ambigua_real]
WHATSAPP_LOG.clear()
EMAIL_LOG.clear()
print(">>> Rodando Cenário 1 de novo, só com a transação ambígua...")
scenario_1_ingest.run()
linha()
cr_amb = {(r["ID Contrato"], r["Parcela"]): r for r in DB[config.ABA_CONTAS_RECEBER]}
check("CTR-AMB-1 continua Aberto (não foi casado às cegas)",
      cr_amb[("CTR-AMB-1", "1/1")]["Status"] == "Aberto")
check("CTR-AMB-2 continua Aberto (não foi casado às cegas)",
      cr_amb[("CTR-AMB-2", "1/1")]["Status"] == "Aberto")
check("Gestor recebeu alerta de transação AMBÍGUA por WhatsApp (texto distinto de 'sem contrato')",
      any("mais de uma parcela candidata" in msg for _, msg in WHATSAPP_LOG),
      f"log: {WHATSAPP_LOG}")
check("Gestor recebeu o mesmo alerta AMBÍGUA por e-mail também",
      any("mais de uma parcela candidata" in corpo for _, _, corpo in EMAIL_LOG),
      f"log: {EMAIL_LOG}")
linha()

WHATSAPP_LOG.clear()
EMAIL_LOG.clear()
print(">>> Rodando Cenário 2 (alertas + atraso)...")
scenario_2_alerts.run()
linha()
cr = {(r["ID Contrato"], r["Parcela"]): r for r in DB[config.ABA_CONTAS_RECEBER]}
check("CTR-005 (vencida há 5 dias) foi marcado Atrasado",
      cr[("CTR-005", "1/1")]["Status"] == "Atrasado")
check("Resumo diário foi enviado ao gestor por WhatsApp",
      len(WHATSAPP_LOG) >= 1)
check("Resumo diário foi enviado ao gestor por e-mail também",
      len(EMAIL_LOG) >= 1, f"log: {EMAIL_LOG}")
linha()

WHATSAPP_LOG.clear()
EMAIL_LOG.clear()
print(">>> Rodando Cenário 3 (comissões sobre contrato assinado)...")
scenario_3_commissions.run()
linha()
com_casa = DB.get(config.EMPRESAS["casa_arvore"]["aba_com"], [])
com_casarao = DB.get(config.EMPRESAS["casarao"]["aba_com"], [])
maria = next((c for c in com_casa if c["Vendedor"] == "Maria"), None)
ana = next((c for c in com_casarao if c["Vendedor"] == "Ana"), None)
check("Maria recebeu comissão sobre CTR-001 (10% de R$2.500 = R$250)",
      maria is not None and abs(maria["Comissão"] - 250.0) < 0.01,
      f"encontrado: {maria}")
check("Ana recebeu comissão sobre CTR-002 (6% de R$8.000 total = R$480)",
      ana is not None and abs(ana["Comissão"] - 480.0) < 0.01,
      f"encontrado: {ana}")
check("João recebeu comissão só de CTR-003 (10% de R$3.200=R$320) — "
      "CTR-005 foi assinado há 20 dias, fora da semana corrente, corretamente excluído",
      any(c["Vendedor"] == "João" and abs(c["Comissão"] - 320.0) < 0.01 for c in com_casa))
check("Maria recebeu o aviso de comissão por WhatsApp",
      any("Maria" in msg for _, msg in WHATSAPP_LOG), f"log: {WHATSAPP_LOG}")
check("Maria recebeu o mesmo aviso de comissão por e-mail também",
      any(dest == config.VENDEDORES["Maria"]["email"] for dest, _, _ in EMAIL_LOG),
      f"log: {EMAIL_LOG}")
linha()

print(">>> Rodando Cenário 6 (DRE com impostos)...")
scenario_6_dre.run()
linha()
dre = DB.get(config.ABA_DRE, [])
dre_casa = next((d for d in dre if d["Empresa"] == "Casa da Árvore"), None)
check("DRE da Casa da Árvore foi gerado", dre_casa is not None)
if dre_casa:
    check("Receita bruta da Casa bate (R$2.500 + R$3.200 = R$5.700)",
          abs(dre_casa["Receita Bruta"] - 5700.0) < 0.01, f"encontrado: {dre_casa['Receita Bruta']}")
    check("Impostos calculados (10% de R$5.700 = R$570)",
          abs(dre_casa["Impostos"] - 570.0) < 0.01, f"encontrado: {dre_casa['Impostos']}")
linha()

WHATSAPP_LOG.clear()
EMAIL_LOG.clear()
print(">>> Rodando Cenário 7 (Real vs Orçado)...")
mes_atual = HOJE.strftime("%Y-%m")
cr_atual = DB[config.ABA_CONTAS_RECEBER]


def _projecao(nome_empresa):
    pago = sum(float(str(p["Valor Parcela"]).replace(",", "."))
               for p in cr_atual if p["Empresa"] == nome_empresa
               and p["Status"] == "Pago"
               and str(p.get("Data Pagamento", "")).startswith(mes_atual))
    a_vencer = sum(float(str(p["Valor Parcela"]).replace(",", "."))
                   for p in cr_atual if p["Empresa"] == nome_empresa
                   and p["Status"] in ("Aberto", "Atrasado")
                   and str(p.get("Vencimento", "")).startswith(mes_atual))
    return pago + a_vencer * 0.9


# meta da Casa da Árvore = a própria projeção -> desvio ~0% (não deve alertar)
# meta do Casarão absurdamente alta -> desvio bem negativo (deve alertar)
DB[config.ABA_METAS] = [
    {"Empresa": "Casa da Árvore", "Meta Mensal": round(_projecao("Casa da Árvore"), 2) or 0.01},
    {"Empresa": "Casarão Festas", "Meta Mensal": 1_000_000.0},
]

scenario_7_budget.run()
linha()
real_orcado = DB.get(config.ABA_REAL_ORCADO, [])
ro_casa = next((r for r in real_orcado if r["Empresa"] == "Casa da Árvore"), None)
ro_casarao = next((r for r in real_orcado if r["Empresa"] == "Casarão Festas"), None)
check("Real vs Orçado da Casa da Árvore foi gravado", ro_casa is not None)
check("Real vs Orçado do Casarão foi gravado", ro_casarao is not None)
if ro_casa:
    check("Casa da Árvore com desvio pequeno (meta = própria projeção) NÃO gera alerta",
          abs(ro_casa["Desvio %"]) <= 10, f"encontrado: {ro_casa['Desvio %']}%")
if ro_casarao:
    check("Casarão com meta irreal tem desvio > 10%",
          abs(ro_casarao["Desvio %"]) > 10, f"encontrado: {ro_casarao['Desvio %']}%")
check("Alerta por WhatsApp cita o Casarão mas não a Casa da Árvore (só quem estourou 10%)",
      len(WHATSAPP_LOG) == 1
      and "Casarão Festas" in WHATSAPP_LOG[0][1]
      and "Casa da Árvore" not in WHATSAPP_LOG[0][1],
      f"log: {WHATSAPP_LOG}")
check("Mesmo alerta chegou por e-mail também, só citando o Casarão",
      len(EMAIL_LOG) == 1
      and "Casarão Festas" in EMAIL_LOG[0][2]
      and "Casa da Árvore" not in EMAIL_LOG[0][2],
      f"log: {EMAIL_LOG}")
linha()

WHATSAPP_LOG.clear()
EMAIL_LOG.clear()
print(">>> Rodando Cenário 4 (relatório executivo semanal)...")
seg_semana = HOJE - timedelta(days=HOJE.weekday())
semana_passada = seg_semana - timedelta(days=7)
# lançamento fora da semana corrente -> não deve entrar no total do relatório
DB.setdefault(config.EMPRESAS["casa_arvore"]["aba_receb"], []).append({
    "Data": semana_passada.isoformat(), "Venue": "Venue Principal",
    "Evento": "Fantasma semana passada", "Cliente": "Ghost", "Valor": 99999,
    "Forma Pagto": "Pix", "Status": "Pago",
    "Data Receb": semana_passada.isoformat(), "Banco": "TESTE"})


def _soma_semana_teste(aba, col_data, col_valor):
    total = 0.0
    for r in DB.get(aba, []):
        d = str(r.get(col_data, ""))
        if seg_semana.isoformat() <= d <= HOJE.isoformat():
            try:
                total += float(str(r[col_valor]).replace(",", "."))
            except (ValueError, KeyError):
                pass
    return total


total_esperado = sum(
    _soma_semana_teste(emp["aba_receb"], "Data Receb", "Valor")
    for emp in config.EMPRESAS.values())
scenario_4_weekly.run()
linha()
check("Relatório semanal foi enviado ao gestor por WhatsApp", len(WHATSAPP_LOG) == 1)
check("Relatório semanal foi enviado ao gestor por e-mail também", len(EMAIL_LOG) == 1,
      f"log: {EMAIL_LOG}")
if WHATSAPP_LOG:
    msg_semanal = WHATSAPP_LOG[0][1]
    check("Relatório (WhatsApp) cita as duas empresas",
          "Casa da Árvore" in msg_semanal and "Casarão Festas" in msg_semanal)
    check(f"Total geral (R$ {total_esperado:,.2f}) exclui o lançamento fantasma da semana passada (R$99.999)",
          f"R$ {total_esperado:,.2f}" in msg_semanal
          and "99,999" not in msg_semanal and "99999" not in msg_semanal,
          f"mensagem: {msg_semanal}")
if EMAIL_LOG:
    check("Relatório (e-mail) cita as duas empresas",
          "Casa da Árvore" in EMAIL_LOG[0][2] and "Casarão Festas" in EMAIL_LOG[0][2])
linha()

WHATSAPP_LOG.clear()
EMAIL_LOG.clear()
print(">>> Rodando Cenário 5 (análise diária com Claude — stub)...")
scenario_5_analysis.run()
linha()
check("Análise diária foi enviada ao gestor por WhatsApp (texto do stub, Claude não chamado de verdade)",
      len(WHATSAPP_LOG) == 1 and "[stub] análise não chamada offline." in WHATSAPP_LOG[0][1])
check("Análise diária foi enviada ao gestor por e-mail também",
      len(EMAIL_LOG) == 1 and "[stub] análise não chamada offline." in EMAIL_LOG[0][2],
      f"log: {EMAIL_LOG}")
check("Prompt enviado ao Claude tratou o Casarão (sem pendências no dataset) como zero, sem quebrar",
      "Casarão Festas: recebido ontem R$0; a vencer no mês R$0; em atraso R$0"
      in _ULTIMO_PROMPT_CLAUDE.get("prompt", ""),
      f"prompt: {_ULTIMO_PROMPT_CLAUDE.get('prompt')}")
linha()

# ---------------------------------------------------------------------------
# 5) RESUMO
# ---------------------------------------------------------------------------
linha("=" * 60)
total = len(falhas)
if total == 0:
    print("🎉 TODOS OS TESTES PASSARAM — lógica de negócio validada.")
else:
    print(f"⚠️  {total} teste(s) falharam: {', '.join(falhas)}")
linha("=" * 60)
print("\nMensagens WhatsApp que teriam sido enviadas nesta rodada:")
for fone, msg in WHATSAPP_LOG:
    print(f"\n→ Para {fone}:\n{msg}")
print("\nE-mails que teriam sido enviados nesta rodada:")
for dest, assunto, corpo in EMAIL_LOG:
    print(f"\n→ Para {dest} — {assunto}:\n{corpo}")

sys.exit(1 if falhas else 0)

"""Painel financeiro — Casa da Árvore + Casarão (só leitura, não edita nada).

Lê direto da mesma planilha Google Sheets que os cenários usam.

Rodar localmente:
    streamlit run painel/app.py
(usa o mesmo credentials.json/.env da raiz do projeto)

Hospedado (Streamlit Community Cloud): as credenciais vêm de st.secrets
em vez do .env — ver README.md, seção "Painel web".
"""
import os
from datetime import date, timedelta
from pathlib import Path

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Financeiro — Casa da Árvore + Casarão",
                    page_icon="📊", layout="wide")

ROOT = Path(__file__).resolve().parent.parent  # raiz do projeto, não depende do cwd
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# par azul/laranja Okabe-Ito — seguro pra daltonismo, usado consistentemente
# pra identificar cada empresa em todo o painel
COR_CASA = "#0072B2"
COR_CASARAO = "#E69F00"
EMPRESAS = [("Casa da Árvore", COR_CASA, "CasaArvore"),
            ("Casarão Festas", COR_CASARAO, "Casarao")]


def _tem_secrets():
    """st.secrets levanta exceção (em vez de agir como dict vazio) quando
    não existe nenhum secrets.toml — o caso normal rodando localmente."""
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


@st.cache_resource
def _cliente():
    if _tem_secrets():
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
        spreadsheet_id = st.secrets["SPREADSHEET_ID"]
    else:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        caminho_credenciais = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        if not os.path.isabs(caminho_credenciais):
            caminho_credenciais = ROOT / caminho_credenciais
        creds = Credentials.from_service_account_file(str(caminho_credenciais), scopes=SCOPES)
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
    return gspread.authorize(creds).open_by_key(spreadsheet_id)


FALHAS_LEITURA = {}


@st.cache_data(ttl=300)
def ler(aba):
    """Lê uma aba como DataFrame sem derrubar o painel.

    Aba ausente, credencial inválida, planilha indisponível ou cabeçalho
    inconsistente são tratados como uma leitura vazia e registrados para o
    aviso operacional exibido na tela. O painel continua útil para as abas
    que conseguirem ser lidas.
    """
    try:
        registros = _cliente().worksheet(aba).get_all_records()
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as exc:  # noqa: BLE001 — a interface não deve cair por uma aba
        FALHAS_LEITURA[aba] = type(exc).__name__
        return pd.DataFrame()
    return pd.DataFrame(registros)


def numero(valor, default=0.0):
    try:
        return float(str(valor).replace(",", "."))
    except (ValueError, TypeError):
        return default


st.title("📊 Financeiro — Casa da Árvore + Casarão")
st.caption(f"Dados de {date.today().strftime('%d/%m/%Y')} · atualiza sozinho a cada 5 min")
if st.button("🔄 Atualizar agora"):
    st.cache_data.clear()
    FALHAS_LEITURA.clear()
    st.rerun()

hoje = date.today()
mes_atual = hoje.strftime("%Y-%m")
seg_semana = hoje - timedelta(days=hoje.weekday())

cr = ler("Contas_a_Receber")
dre = ler("DRE_Automatico")
real_orcado = ler("RealVsOrcado")

if FALHAS_LEITURA:
    abas = ", ".join(sorted(FALHAS_LEITURA))
    st.warning(
        "Não foi possível ler algumas abas da planilha ("
        f"{abas}). O painel exibirá zeros ou mensagens de ausência até que "
        "as credenciais e os cabeçalhos sejam corrigidos."
    )

# ---------------------------------------------------------------------------
# KPIs por empresa
# ---------------------------------------------------------------------------
cols = st.columns(2)
for (nome, cor, sufixo), col in zip(EMPRESAS, cols):
    with col:
        st.markdown(f"### :{'blue' if cor == COR_CASA else 'orange'}[{nome}]")
        receb = ler(f"Recebimentos_{sufixo}")
        desp = ler(f"Despesas_{sufixo}")

        receita_mes = 0.0
        if not receb.empty and "Data Receb" in receb.columns:
            no_mes = receb[receb["Data Receb"].astype(str).str.startswith(mes_atual)]
            receita_mes = no_mes["Valor"].apply(numero).sum()

        despesa_mes = 0.0
        if not desp.empty and "Data" in desp.columns:
            no_mes = desp[desp["Data"].astype(str).str.startswith(mes_atual)]
            despesa_mes = no_mes["Valor"].apply(numero).sum()

        em_atraso = 0.0
        if not cr.empty and "Empresa" in cr.columns:
            filtro = (cr["Empresa"] == nome) & (cr["Status"] == "Atrasado")
            em_atraso = cr[filtro]["Valor Parcela"].apply(numero).sum()

        k1, k2, k3 = st.columns(3)
        k1.metric("Receita do mês", f"R$ {receita_mes:,.0f}")
        k2.metric("Despesas do mês", f"R$ {despesa_mes:,.0f}")
        k3.metric("Em atraso", f"R$ {em_atraso:,.0f}")

st.divider()

# ---------------------------------------------------------------------------
# DRE do mês
# ---------------------------------------------------------------------------
st.subheader("DRE do mês")
if not dre.empty and "Mês" in dre.columns:
    dre_mes = dre[dre["Mês"] == mes_atual]
    if not dre_mes.empty:
        st.dataframe(
            dre_mes.set_index("Empresa")[
                ["Receita Bruta", "Impostos", "Custos Variáveis", "Comissões",
                 "Custos Fixos", "Lucro Operacional", "Margem %"]],
            use_container_width=True)
    else:
        st.info("Ainda não rodou o Cenário 6 (DRE) este mês.")
else:
    st.info("Nenhum DRE gerado ainda.")

st.divider()

# ---------------------------------------------------------------------------
# Real vs Orçado
# ---------------------------------------------------------------------------
st.subheader("Real vs Orçado (mais recente)")
if not real_orcado.empty and "Data" in real_orcado.columns:
    ultimo_por_empresa = real_orcado.sort_values("Data").groupby("Empresa").tail(1)
    st.dataframe(
        ultimo_por_empresa.set_index("Empresa")[["Meta", "Pago", "A Vencer", "Projeção", "Desvio %"]],
        use_container_width=True)
else:
    st.info("Nenhum dado de Real vs Orçado ainda.")

st.divider()

# ---------------------------------------------------------------------------
# Comissões da semana
# ---------------------------------------------------------------------------
st.subheader(f"Comissões — semana de {seg_semana.strftime('%d/%m')}")
com_casa = ler("Comissoes_CasaArvore")
com_casarao = ler("Comissoes_Casarao")
partes = [df for df in (com_casa, com_casarao) if not df.empty]
comissoes = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
if not comissoes.empty and "Semana" in comissoes.columns:
    semana_atual = comissoes[comissoes["Semana"] == seg_semana.isoformat()]
    if not semana_atual.empty:
        st.dataframe(
            semana_atual[["Vendedor", "Contratos", "Base", "Comissão", "Estorno", "Líquido", "Status"]],
            use_container_width=True)
    else:
        st.info("Comissões desta semana ainda não foram calculadas (Cenário 3 roda sexta 18:00).")
else:
    st.info("Nenhuma comissão registrada ainda.")

st.divider()

# ---------------------------------------------------------------------------
# Contratos em atraso (detalhe)
# ---------------------------------------------------------------------------
st.subheader("Contratos em atraso")
if not cr.empty and "Status" in cr.columns:
    atrasados = cr[cr["Status"] == "Atrasado"]
    if not atrasados.empty:
        colunas = [c for c in ["Cliente", "Empresa", "Evento", "Valor Parcela",
                                "Vencimento", "Fone Cliente", "Email Cliente"]
                   if c in atrasados.columns]
        st.dataframe(atrasados[colunas], use_container_width=True, hide_index=True)
    else:
        st.success("Nenhum contrato em atraso agora. 🎉")
else:
    st.info("Sem dados de Contas_a_Receber ainda.")

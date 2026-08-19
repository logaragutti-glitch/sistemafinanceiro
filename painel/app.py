"""Painel executivo do Sistema Financeiro Casa da Árvore + Casarão.

A interface é somente leitura: todos os dados continuam vindo das mesmas abas
Google Sheets utilizadas pelos cenários financeiros. O redesign organiza a
informação por decisão, não por ordem de execução técnica.
"""
from __future__ import annotations

import calendar
import mimetypes
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import gspread
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Painel Financeiro | Casa da Árvore + Casarão",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cashflow import consolidar, totais
from src import drive_uploads
from src.upload_utils import validar_agendamentos_csv, validar_upload_extrato

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
COR_CASA = "#1769AA"
COR_CASARAO = "#C97916"
COR_VERDE = "#16845B"
COR_VERMELHO = "#C44536"
COR_AMARELO = "#A66A00"
COR_TEXTO = "#17212B"
COR_MUTED = "#61707D"
COR_BORDA = "#DCE3E8"

EMPRESAS = ["Casa da Árvore", "Casarão Festas"]
PAGINAS = ["Resumo", "Importações", "Agendamentos", "Fluxo de caixa", "Recebimentos", "Despesas", "Contratos", "DRE", "Comissões", "Operação"]
ABAS = {
    "Contas a receber": "Contas_a_Receber",
    "Custos fixos": "Custos_Fixos",
    "DRE": "DRE_Automatico",
    "Real vs orçado": "RealVsOrcado",
    "Metas": "Metas_Mensais",
    "Recebimentos Casa": "Recebimentos_CasaArvore",
    "Despesas Casa": "Despesas_CasaArvore",
    "Comissões Casa": "Comissoes_CasaArvore",
    "Recebimentos Casarão": "Recebimentos_Casarao",
    "Despesas Casarão": "Despesas_Casarao",
    "Comissões Casarão": "Comissoes_Casarao",
    "Agendamentos": "Agendamentos",
}

CSS = f"""
<style>
    :root {{
        --ink: {COR_TEXTO};
        --muted: {COR_MUTED};
        --border: {COR_BORDA};
        --surface: #ffffff;
        --surface-soft: #f5f7f9;
    }}
    .stApp {{ background: #f7f9fb; color: var(--ink); }}
    [data-testid="stHeader"] {{ background: rgba(247,249,251,.92); }}
    [data-testid="stSidebar"] {{ background: #ffffff; border-right: 1px solid var(--border); }}
    [data-testid="stSidebar"] hr {{ margin: 1rem 0; border-color: var(--border); }}
    [data-testid="stSidebar"] [data-testid="stRadio"] {{ width: 100%; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioGroup"] {{ gap: .22rem; width: 100%; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"] {{
        color: var(--ink) !important; opacity: 1 !important; width: 100%;
        border-radius: 9px; transition: background .15s ease;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"] > div {{
        width: 100%; border-radius: 9px; padding: .14rem .28rem;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"] p,
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"] span,
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] {{
        color: var(--ink) !important; opacity: 1 !important; visibility: visible !important;
        font-size: .9rem !important; font-weight: 600 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked) > div {{
        background: #e7f1f8 !important; color: {COR_CASA} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked) p,
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked) span,
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked) [data-testid="stMarkdownContainer"] {{
        color: {COR_CASA} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioOption"]:hover > div {{ background: #f1f5f7 !important; }}
    h1, h2, h3 {{ color: var(--ink); letter-spacing: -0.02em; }}
    h1 {{ font-size: 2.15rem !important; margin: .1rem 0 .25rem !important; }}
    h2 {{ font-size: 1.28rem !important; margin-top: .2rem !important; }}
    h3 {{ font-size: 1rem !important; }}
    .block-container {{ max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }}
    .brand-mark {{
        display: inline-flex; align-items: center; justify-content: center;
        width: 38px; height: 38px; border-radius: 11px;
        background: linear-gradient(135deg, {COR_CASA}, #3f8fc6);
        color: white; font-weight: 800; font-size: 1.15rem; margin-bottom: .65rem;
    }}
    .brand-name {{ font-weight: 750; font-size: 1.05rem; color: var(--ink); line-height: 1.2; }}
    .brand-subtitle {{ color: var(--muted); font-size: .76rem; margin-top: .15rem; line-height: 1.35; }}
    .eyebrow {{ color: {COR_CASA}; font-weight: 750; font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .35rem; }}
    .page-subtitle {{ color: var(--muted); font-size: .93rem; margin-bottom: 1.25rem; }}
    .status-pill {{ display: inline-flex; align-items: center; gap: .4rem; padding: .4rem .72rem; border-radius: 999px; font-size: .78rem; font-weight: 650; }}
    .status-ok {{ background: #e8f5ef; color: #146b4b; }}
    .status-warn {{ background: #fff4dc; color: #8a5900; }}
    .metric-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1rem 1.05rem .95rem; min-height: 118px; box-shadow: 0 3px 12px rgba(28,51,67,.035); }}
    .metric-label {{ color: var(--muted); font-size: .76rem; font-weight: 650; text-transform: uppercase; letter-spacing: .045em; }}
    .metric-value {{ color: var(--ink); font-size: 1.55rem; font-weight: 780; letter-spacing: -.03em; margin-top: .35rem; }}
    .metric-note {{ color: var(--muted); font-size: .76rem; margin-top: .3rem; }}
    .company-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.1rem 1.15rem; box-shadow: 0 3px 12px rgba(28,51,67,.035); }}
    .company-name {{ font-size: 1.05rem; font-weight: 760; margin-bottom: .9rem; }}
    .company-name.casa {{ color: {COR_CASA}; }}
    .company-name.casarao {{ color: {COR_CASARAO}; }}
    .company-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; }}
    .company-stat-label {{ color: var(--muted); font-size: .72rem; }}
    .company-stat-value {{ color: var(--ink); font-size: 1rem; font-weight: 740; margin-top: .16rem; }}
    .progress-track {{ height: 8px; border-radius: 99px; background: #edf0f2; overflow: hidden; margin-top: .55rem; }}
    .progress-fill {{ height: 100%; border-radius: 99px; background: {COR_VERDE}; }}
    .section-heading {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin: 1.65rem 0 .7rem; }}
    .section-heading h2 {{ margin: 0 !important; }}
    .section-caption {{ color: var(--muted); font-size: .82rem; }}
    .attention-card {{ background: #fffdf8; border: 1px solid #f0dfb7; border-left: 4px solid {COR_AMARELO}; border-radius: 12px; padding: .78rem .9rem; margin-bottom: .55rem; }}
    .attention-card.danger {{ background: #fff9f8; border-color: #f2c9c4; border-left-color: {COR_VERMELHO}; }}
    .attention-title {{ color: var(--ink); font-weight: 700; font-size: .88rem; }}
    .attention-text {{ color: var(--muted); font-size: .8rem; margin-top: .2rem; }}
    .empty-state {{ background: var(--surface); border: 1px dashed var(--border); border-radius: 14px; padding: 1.1rem 1.15rem; color: var(--muted); }}
    .empty-title {{ color: var(--ink); font-weight: 700; margin-bottom: .2rem; }}
    .side-note {{ color: var(--muted); font-size: .76rem; line-height: 1.45; }}
    .small-kpi {{ color: var(--muted); font-size: .8rem; }}
    .small-kpi strong {{ color: var(--ink); font-size: 1.15rem; display: block; margin-top: .15rem; }}
    div[data-testid="stDataFrame"] {{ border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
    @media (max-width: 900px) {{
        h1 {{ font-size: 1.75rem !important; }}
        .company-grid {{ grid-template-columns: repeat(2, 1fr); }}
        .metric-card {{ min-height: 105px; }}
    }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


FALHAS_LEITURA: dict[str, str] = {}


def _tem_secrets() -> bool:
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


@st.cache_resource
def _cliente():
    if _tem_secrets():
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPES
        )
        spreadsheet_id = st.secrets["SPREADSHEET_ID"]
    else:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        caminho = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        if not os.path.isabs(caminho):
            caminho = str(ROOT / caminho)
        creds = Credentials.from_service_account_file(caminho, scopes=SCOPES)
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
    return gspread.authorize(creds).open_by_key(spreadsheet_id)


@st.cache_resource
def _drive():
    if _tem_secrets():
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=DRIVE_SCOPES
        )
        folder_id = str(st.secrets.get("DRIVE_UPLOADS_FOLDER_ID", "")) or None
    else:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        caminho = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        if not os.path.isabs(caminho):
            caminho = str(ROOT / caminho)
        creds = Credentials.from_service_account_file(caminho, scopes=DRIVE_SCOPES)
        folder_id = os.getenv("DRIVE_UPLOADS_FOLDER_ID") or None
    return drive_uploads.service(creds), folder_id


@st.cache_data(ttl=300)
def ler(aba: str) -> pd.DataFrame:
    try:
        registros = _cliente().worksheet(aba).get_all_records()
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as exc:  # noqa: BLE001 — o painel deve permanecer acessível
        FALHAS_LEITURA[aba] = type(exc).__name__
        return pd.DataFrame()
    return pd.DataFrame(registros)


def _gravar_linhas(aba: str, registros: list[dict]) -> int:
    if not registros:
        return 0
    worksheet = _cliente().worksheet(aba)
    headers = worksheet.row_values(1)
    if not headers:
        raise ValueError(f"A aba {aba} não possui headers")
    linhas = [[registro.get(header, "") for header in headers] for registro in registros]
    worksheet.append_rows(linhas, value_input_option="USER_ENTERED")
    ler.clear()
    return len(linhas)


def gravar_agendamento(dados: dict) -> None:
    """Grava um agendamento na planilha; nunca lança direto em realizado."""
    _gravar_linhas(ABAS["Agendamentos"], [dados])


def numero(valor: object, default: float = 0.0) -> float:
    if valor is None:
        return default
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
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


def moeda(valor: object) -> str:
    valor_num = numero(valor)
    sinal = "-" if valor_num < 0 else ""
    return f"{sinal}R$ {abs(valor_num):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percentual(valor: object) -> str:
    valor_num = numero(valor)
    if abs(valor_num) <= 1:
        valor_num *= 100
    return f"{valor_num:.1f}%".replace(".", ",")


def filtrar_empresa(df: pd.DataFrame, empresa: str) -> pd.DataFrame:
    if df.empty or empresa == "Todas" or "Empresa" not in df.columns:
        return df.copy()
    return df[df["Empresa"].astype(str) == empresa].copy()


def filtrar_periodo(df: pd.DataFrame, coluna: str, periodo: str) -> pd.DataFrame:
    if df.empty or coluna not in df.columns:
        return df.copy()
    return df[df[coluna].astype(str).str.startswith(periodo)].copy()


def filtrar_venue(df: pd.DataFrame, venue: str) -> pd.DataFrame:
    if df.empty or venue == "Todos os venues" or "Venue" not in df.columns:
        return df.copy()
    return df[df["Venue"].astype(str) == venue].copy()


def soma(df: pd.DataFrame, coluna: str) -> float:
    if df.empty or coluna not in df.columns:
        return 0.0
    return float(df[coluna].apply(numero).sum())


def serie_monetaria(df: pd.DataFrame, coluna_data: str, coluna_valor: str, periodo: str) -> pd.DataFrame:
    if df.empty or coluna_data not in df.columns or coluna_valor not in df.columns:
        return pd.DataFrame(columns=["Data", "Valor"])
    trabalho = df.copy()
    trabalho["Data"] = trabalho[coluna_data].astype(str).str[:10]
    trabalho = trabalho[trabalho["Data"].str.startswith(periodo)]
    trabalho["Valor"] = trabalho[coluna_valor].apply(numero)
    return trabalho.groupby("Data", as_index=False)["Valor"].sum()


def periodo_opcoes(frames: dict[str, pd.DataFrame]) -> list[str]:
    opcoes = set()
    hoje = date.today().replace(day=1)
    for meses_atras in range(12):
        mes = hoje.month - meses_atras
        ano = hoje.year
        while mes <= 0:
            mes += 12
            ano -= 1
        opcoes.add(f"{ano:04d}-{mes:02d}")
    for df, colunas in [
        (frames["Contas a receber"], ["Vencimento", "Data Assinatura"]),
        (frames["Recebimentos Casa"], ["Data", "Data Receb"]),
        (frames["Despesas Casa"], ["Data"]),
        (frames["DRE"], ["Mês"]),
        (frames["Real vs orçado"], ["Data"]),
    ]:
        if not df.empty:
            for coluna in colunas:
                if coluna in df.columns:
                    opcoes.update(
                        valor[:7] for valor in df[coluna].astype(str).tolist() if len(valor) >= 7
                    )
    return sorted(opcoes, reverse=True)


def meta_por_empresa(metas: pd.DataFrame) -> dict[str, float]:
    if metas.empty or "Empresa" not in metas.columns:
        return {}
    return {
        str(row["Empresa"]): numero(row.get("Meta Mensal"))
        for _, row in metas.iterrows()
        if str(row.get("Empresa", "")).strip()
    }


def formatar_df(df: pd.DataFrame, colunas_moeda: tuple[str, ...] = ()) -> pd.DataFrame:
    view = df.copy()
    for coluna in colunas_moeda:
        if coluna in view.columns:
            view[coluna] = view[coluna].apply(moeda)
    return view


def empty_state(titulo: str, texto: str) -> None:
    st.markdown(
        f'<div class="empty-state"><div class="empty-title">{titulo}</div>'
        f'<div>{texto}</div></div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def chart_layout(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=8, r=8, t=18, b=8),
        font=dict(family="Arial, sans-serif", color=COR_TEXTO, size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=COR_BORDA)
    fig.update_yaxes(showgrid=True, gridcolor="#eef1f3", zeroline=False)
    return fig


def render_header(periodo: str, empresa: str, titulo: str = "Visão geral financeira") -> None:
    col_titulo, col_status, col_acao = st.columns([2.6, 1.3, .7])
    with col_titulo:
        st.markdown('<div class="eyebrow">Painel executivo</div>', unsafe_allow_html=True)
        st.title(titulo)
        escopo = "todas as empresas" if empresa == "Todas" else empresa
        st.markdown(
            f'<div class="page-subtitle">Acompanhe receita, despesas, metas e riscos de {escopo.lower()} · período {periodo}</div>',
            unsafe_allow_html=True,
        )
    with col_status:
        if FALHAS_LEITURA:
            st.markdown('<span class="status-pill status-warn">● Atenção na conexão</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-pill status-ok">● Planilha conectada</span>', unsafe_allow_html=True)
        st.caption(f"Atualização automática a cada 5 min")
    with col_acao:
        if st.button("Atualizar", use_container_width=True):
            st.cache_data.clear()
            FALHAS_LEITURA.clear()
            st.rerun()


def render_sidebar(frames: dict[str, pd.DataFrame]) -> tuple[str, str, str, str]:
    with st.sidebar:
        st.markdown('<div class="brand-mark">FA</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-name">Financeiro</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-subtitle">Casa da Árvore + Casarão</div>', unsafe_allow_html=True)
        st.divider()
        pagina = st.radio("Navegação", PAGINAS, label_visibility="visible")
        st.divider()
        st.markdown("**Filtros do painel**")
        periodos = periodo_opcoes(frames)
        periodo = st.selectbox("Período", periodos, index=0)
        empresa = st.selectbox("Empresa", ["Todas"] + EMPRESAS)
        venues = {"Todos os venues"}
        for chave in ("Contas a receber", "Recebimentos Casa", "Despesas Casa", "Recebimentos Casarão", "Despesas Casarão"):
            df = frames[chave]
            if not df.empty and "Venue" in df.columns:
                venues.update(str(v) for v in df["Venue"].dropna().unique() if str(v).strip())
        venue = st.selectbox("Venue / unidade", sorted(venues))
        st.divider()
        if FALHAS_LEITURA:
            st.markdown('<div class="side-note">Algumas abas não puderam ser lidas. O painel continua disponível, mas os indicadores afetados podem aparecer vazios.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="side-note">O realizado é somente leitura e vem dos cenários automáticos. A página Agendamentos permite registrar compromissos futuros para o fluxo projetado.</div>', unsafe_allow_html=True)
    return pagina, periodo, empresa, venue


def preparar_frames() -> dict[str, pd.DataFrame]:
    return {nome: ler(aba) for nome, aba in ABAS.items()}


def dados_filtrados(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> dict[str, pd.DataFrame]:
    resultado = {}
    for chave, df in frames.items():
        filtrado = filtrar_empresa(df, empresa)
        if chave in {"Contas a receber"}:
            filtrado = filtrar_periodo(filtrado, "Vencimento", periodo)
        elif chave in {"Recebimentos Casa", "Recebimentos Casarão", "Despesas Casa", "Despesas Casarão"}:
            filtrado = filtrar_periodo(filtrado, "Data", periodo)
        elif chave == "DRE":
            filtrado = filtrar_periodo(filtrado, "Mês", periodo)
        elif chave == "Real vs orçado":
            filtrado = filtrar_periodo(filtrado, "Data", periodo)
        resultado[chave] = filtrar_venue(filtrado, venue)
    return resultado


def linhas_fluxo(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> list[dict]:
    """Consolida realizado e previsto para o mês selecionado."""
    filtrados = dados_filtrados(frames, periodo, empresa, venue)
    recebimentos, despesas = recebimentos_despesas(filtrados)
    inicio = date.fromisoformat(f"{periodo}-01")
    ultimo_dia = calendar.monthrange(inicio.year, inicio.month)[1]
    fim = date(inicio.year, inicio.month, ultimo_dia)
    return consolidar(
        recebimentos.to_dict("records"),
        despesas.to_dict("records"),
        filtrados["Contas a receber"].to_dict("records"),
        filtrados["Agendamentos"].to_dict("records"),
        inicio,
        fim,
    )


def recebimentos_despesas(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    recebimentos = [frames[k] for k in ("Recebimentos Casa", "Recebimentos Casarão") if not frames[k].empty]
    despesas = [frames[k] for k in ("Despesas Casa", "Despesas Casarão") if not frames[k].empty]
    return (
        pd.concat(recebimentos, ignore_index=True) if recebimentos else pd.DataFrame(),
        pd.concat(despesas, ignore_index=True) if despesas else pd.DataFrame(),
    )


def construir_alertas(frames: dict[str, pd.DataFrame], empresa: str) -> list[tuple[str, str, bool]]:
    alertas: list[tuple[str, str, bool]] = []
    cr = filtrar_empresa(frames["Contas a receber"], empresa)
    if cr.empty:
        alertas.append(("Cadastre os contratos", "A aba Contas_a_Receber ainda não possui parcelas para o sistema acompanhar.", False))
    elif "Status" in cr.columns:
        atrasados = cr[cr["Status"].astype(str) == "Atrasado"]
        if not atrasados.empty:
            alertas.append(("Contratos em atraso", f"{len(atrasados)} parcela(s) em atraso, totalizando {moeda(soma(atrasados, 'Valor Parcela'))}.", True))
    orcado = filtrar_empresa(frames["Real vs orçado"], empresa)
    if not orcado.empty and "Desvio %" in orcado.columns:
        desvios = orcado[orcado["Desvio %"].apply(numero).abs() > 0.10]
        if not desvios.empty:
            alertas.append(("Desvio orçamentário", f"Há {len(desvios)} registro(s) com desvio superior a 10%.", True))
    if FALHAS_LEITURA:
        alertas.append(("Verifique a conexão", "Algumas abas não puderam ser lidas; confira credenciais e permissões da planilha.", True))
    return alertas


def card_empresa(nome: str, receb: pd.DataFrame, desp: pd.DataFrame, cr: pd.DataFrame, metas: dict[str, float]) -> None:
    receita = soma(receb, "Valor")
    despesa = soma(desp, "Valor")
    resultado = receita - despesa
    atraso = soma(cr[cr["Status"].astype(str) == "Atrasado"], "Valor Parcela") if not cr.empty and "Status" in cr.columns else 0.0
    meta = metas.get(nome, 0.0)
    progresso = min(max((receita / meta) if meta else 0.0, 0.0), 1.0)
    classe = "casa" if nome == "Casa da Árvore" else "casarao"
    st.markdown(
        f'<div class="company-card"><div class="company-name {classe}">{nome}</div>'
        '<div class="company-grid">'
        f'<div><div class="company-stat-label">Receita</div><div class="company-stat-value">{moeda(receita)}</div></div>'
        f'<div><div class="company-stat-label">Despesas</div><div class="company-stat-value">{moeda(despesa)}</div></div>'
        f'<div><div class="company-stat-label">Resultado</div><div class="company-stat-value">{moeda(resultado)}</div></div>'
        '</div>'
        f'<div style="margin-top:1rem"><div class="company-stat-label">Meta mensal: {moeda(meta) if meta else "não configurada"}</div>'
        f'<div class="progress-track"><div class="progress-fill" style="width:{progresso * 100:.1f}%"></div></div>'
        f'<div class="company-stat-label" style="margin-top:.35rem">{percentual(progresso)} atingido · Em atraso: {moeda(atraso)}</div></div></div>',
        unsafe_allow_html=True,
    )


def pagina_resumo(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa)
    filtrados = dados_filtrados(frames, periodo, empresa, venue)
    receb, desp = recebimentos_despesas(filtrados)
    cr = filtrados["Contas a receber"]
    metas = meta_por_empresa(frames["Metas"])
    receita = soma(receb, "Valor")
    despesas = soma(desp, "Valor")
    resultado = receita - despesas
    atraso = soma(cr[cr["Status"].astype(str) == "Atrasado"], "Valor Parcela") if not cr.empty and "Status" in cr.columns else 0.0
    meta = sum(metas.values()) if empresa == "Todas" else metas.get(empresa, 0.0)
    atingimento = (receita / meta) if meta else 0.0
    st.markdown('<div class="section-heading"><h2>Resumo do período</h2><span class="section-caption">Visão executiva para decisão rápida</span></div>', unsafe_allow_html=True)
    kpis = st.columns(5)
    with kpis[0]: metric_card("Receita recebida", moeda(receita), "No período selecionado")
    with kpis[1]: metric_card("Despesas pagas", moeda(despesas), "No período selecionado")
    with kpis[2]: metric_card("Resultado", moeda(resultado), "Receita menos despesas")
    with kpis[3]: metric_card("Em atraso", moeda(atraso), "Parcelas vencidas")
    with kpis[4]: metric_card("Meta atingida", percentual(atingimento), f"Meta: {moeda(meta) if meta else 'não configurada'}")

    caixa = totais(linhas_fluxo(frames, periodo, empresa, venue))
    st.markdown('<div class="section-heading"><h2>Planejamento do caixa</h2><span class="section-caption">Realizado + lançamentos futuros</span></div>', unsafe_allow_html=True)
    caixa_cols = st.columns(3)
    with caixa_cols[0]: metric_card("Entradas previstas", moeda(caixa["entradas_previstas"]), "Parcelas abertas ou atrasadas")
    with caixa_cols[1]: metric_card("Saídas agendadas", moeda(caixa["saidas_previstas"]), "Despesas futuras")
    with caixa_cols[2]: metric_card("Saldo projetado", moeda(caixa["liquido_projetado"]), "Não altera o realizado")

    st.markdown('<div class="section-heading"><h2>Comparação entre empresas</h2><span class="section-caption">Mesmo período e filtros selecionados</span></div>', unsafe_allow_html=True)
    colunas = st.columns(2)
    for col, nome in zip(colunas, EMPRESAS):
        with col:
            receb_emp = filtrar_empresa(filtrar_periodo(frames["Recebimentos Casa"] if nome == EMPRESAS[0] else frames["Recebimentos Casarão"], "Data", periodo), nome)
            desp_emp = filtrar_empresa(filtrar_periodo(frames["Despesas Casa"] if nome == EMPRESAS[0] else frames["Despesas Casarão"], "Data", periodo), nome)
            cr_emp = filtrar_empresa(filtrar_periodo(frames["Contas a receber"], "Vencimento", periodo), nome)
            cr_emp = filtrar_venue(cr_emp, venue)
            card_empresa(nome, filtrar_venue(receb_emp, venue), filtrar_venue(desp_emp, venue), cr_emp, metas)

    st.markdown('<div class="section-heading"><h2>Movimento financeiro</h2><span class="section-caption">Recebimentos e despesas por dia</span></div>', unsafe_allow_html=True)
    receb_serie = serie_monetaria(receb, "Data", "Valor", periodo)
    desp_serie = serie_monetaria(desp, "Data", "Valor", periodo)
    if receb_serie.empty and desp_serie.empty:
        empty_state("Ainda não há movimento registrado", "Quando os cenários começarem a processar os extratos, a evolução diária aparecerá aqui.")
    else:
        datas = sorted(set(receb_serie.get("Data", [])) | set(desp_serie.get("Data", [])))
        fig = go.Figure()
        if not receb_serie.empty:
            fig.add_trace(go.Scatter(x=receb_serie["Data"], y=receb_serie["Valor"], name="Recebimentos", mode="lines+markers", line=dict(color=COR_CASA, width=3)))
        if not desp_serie.empty:
            fig.add_trace(go.Scatter(x=desp_serie["Data"], y=desp_serie["Valor"], name="Despesas", mode="lines+markers", line=dict(color=COR_CASARAO, width=3)))
        fig.update_yaxes(tickprefix="R$ ", separatethousands=True)
        st.plotly_chart(chart_layout(fig), use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns([1.15, .85])
    with left:
        st.markdown('<div class="section-heading"><h2>Real vs orçado</h2><span class="section-caption">Última projeção disponível</span></div>', unsafe_allow_html=True)
        orcado = filtrados["Real vs orçado"]
        if orcado.empty:
            empty_state("Sem projeção para este período", "O Cenário 7 preencherá esta seção quando houver parcelas e movimentação financeira.")
        else:
            ultimo = orcado.sort_values("Data").groupby("Empresa").tail(1) if "Empresa" in orcado.columns and "Data" in orcado.columns else orcado
            fig = go.Figure()
            for coluna, nome, cor in (("Pago", "Pago", COR_CASA), ("Projeção", "Projeção", COR_CASARAO), ("Meta", "Meta", COR_VERDE)):
                if coluna in ultimo.columns:
                    fig.add_trace(go.Bar(x=ultimo.get("Empresa", pd.Series(["Total"] * len(ultimo))), y=ultimo[coluna].apply(numero), name=nome, marker_color=cor))
            fig.update_layout(barmode="group")
            fig.update_yaxes(tickprefix="R$ ", separatethousands=True)
            st.plotly_chart(chart_layout(fig, 320), use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown('<div class="section-heading"><h2>Requer atenção</h2><span class="section-caption">Prioridades do período</span></div>', unsafe_allow_html=True)
        alertas = construir_alertas(frames, empresa)
        if not alertas:
            st.markdown('<div class="empty-state"><div class="empty-title">Tudo em ordem</div><div>Nenhum alerta prioritário foi identificado com os dados disponíveis.</div></div>', unsafe_allow_html=True)
        else:
            for titulo, texto, perigo in alertas[:5]:
                classe = " danger" if perigo else ""
                st.markdown(f'<div class="attention-card{classe}"><div class="attention-title">{titulo}</div><div class="attention-text">{texto}</div></div>', unsafe_allow_html=True)


def _ler_contratos_upload(conteudo: bytes) -> list[dict]:
    from scripts.importar_contas_receber import ler_csv
    with tempfile.NamedTemporaryFile(suffix=".csv") as temporario:
        temporario.write(conteudo)
        temporario.flush()
        return ler_csv(temporario.name)


def pagina_importacoes(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Importações")
    st.markdown('<div class="eyebrow">Central de entrada</div><div class="page-subtitle">Este é o caminho único para colocar os dados financeiros no sistema.</div>', unsafe_allow_html=True)
    st.info("Siga a ordem: 1) contratos, 2) extratos bancários, 3) compromissos futuros. Cada arquivo é validado e pré-visualizado antes da gravação.")

    st.markdown('<div class="section-heading"><h2>Comece aqui</h2><span class="section-caption">Checklist da primeira configuração</span></div>', unsafe_allow_html=True)
    status_cols = st.columns(4)
    status_items = [
        ("1. Contratos", len(frames["Contas a receber"]), "parcelas cadastradas", "Preencha a base de recebíveis"),
        ("2. Metas", len(frames["Metas"]), "linhas configuradas", "Confira as metas mensais"),
        ("3. Agendamentos", len(frames["Agendamentos"]), "compromissos futuros", "Registre entradas e saídas"),
        ("4. Extratos", "OFX/XLSX", "seis contas", "Envie na aba ao lado"),
    ]
    for coluna, item in zip(status_cols, status_items):
        with coluna:
            if isinstance(item[1], int):
                metric_card(item[0], str(item[1]), item[2])
            else:
                metric_card(item[0], item[1], item[2])
    st.caption("Depois dos uploads, use a página Fluxo de caixa para conferir o realizado e o projetado. Credenciais e senhas não devem ser enviadas por esta tela; elas permanecem protegidas nos Secrets do ambiente.")

    with st.expander("Modelos para baixar antes de preencher", expanded=False):
        st.write("Baixe o modelo correspondente, preencha somente com dados reais e envie na aba correta.")
        modelo_contratos = (ROOT / "templates" / "contas_a_receber.csv").read_bytes()
        modelo_agendamentos = (ROOT / "templates" / "agendamentos.csv").read_bytes()
        download_cols = st.columns(2)
        with download_cols[0]:
            st.download_button("Baixar modelo de contratos", modelo_contratos, "contas_a_receber.csv", "text/csv", use_container_width=True)
        with download_cols[1]:
            st.download_button("Baixar modelo de agendamentos", modelo_agendamentos, "agendamentos.csv", "text/csv", use_container_width=True)

    contratos_tab, extratos_tab, agendamentos_tab = st.tabs(["1. Contratos", "2. Extratos bancários", "3. Agendamentos"])

    with contratos_tab:
        st.markdown("#### Importar contratos e parcelas")
        st.caption("Use um CSV baseado no modelo de Contas_a_Receber. O sistema rejeita campos inválidos e ignora ID Contrato + Parcela já existentes.")
        arquivo = st.file_uploader("Selecione o CSV de contratos", type=["csv"], key="upload_contratos")
        if arquivo is not None:
            try:
                linhas = _ler_contratos_upload(arquivo.getvalue())
                existentes = {(str(l.get("ID Contrato")), str(l.get("Parcela"))) for l in frames["Contas a receber"].to_dict("records")}
                novas = [l for l in linhas if (l["ID Contrato"], l["Parcela"]) not in existentes]
                st.success(f"{len(linhas)} linha(s) válida(s); {len(novas)} nova(s) e {len(linhas) - len(novas)} já existente(s).")
                st.dataframe(pd.DataFrame(linhas).head(20), use_container_width=True, hide_index=True)
                confirmar = st.checkbox("Confirmo que este arquivo contém contratos reais e revisados.", key="confirmar_contratos")
                if st.button("Importar contratos novos", type="primary", disabled=not novas or not confirmar, key="btn_importar_contratos"):
                    quantidade = _gravar_linhas(ABAS["Contas a receber"], novas)
                    st.success(f"{quantidade} contrato(s)/parcela(s) importado(s) com sucesso.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001 — erro de arquivo deve ser exibido sem stack trace
                st.error(f"Arquivo rejeitado: {exc}")

    with agendamentos_tab:
        st.markdown("#### Importar agendamentos em lote")
        st.caption("O CSV deve conter Tipo, Empresa, Descrição, Valor e Data Prevista. Os registros entram no caixa projetado, não no realizado.")
        arquivo = st.file_uploader("Selecione o CSV de agendamentos", type=["csv"], key="upload_agendamentos")
        if arquivo is not None:
            try:
                linhas = validar_agendamentos_csv(arquivo.getvalue())
                existentes = {str(l.get("ID Agendamento")) for l in frames["Agendamentos"].to_dict("records")}
                novas = [l for l in linhas if l["ID Agendamento"] not in existentes]
                st.success(f"{len(linhas)} linha(s) válida(s); {len(novas)} nova(s) e {len(linhas) - len(novas)} já existente(s).")
                st.dataframe(pd.DataFrame(linhas).head(20), use_container_width=True, hide_index=True)
                confirmar = st.checkbox("Confirmo que os agendamentos são compromissos reais e revisados.", key="confirmar_agendamentos")
                if st.button("Importar agendamentos novos", type="primary", disabled=not novas or not confirmar, key="btn_importar_agendamentos"):
                    quantidade = _gravar_linhas(ABAS["Agendamentos"], novas)
                    st.success(f"{quantidade} agendamento(s) importado(s) com sucesso.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Arquivo rejeitado: {exc}")

    with extratos_tab:
        st.markdown("#### Enviar extratos bancários")
        st.caption("Envie um arquivo por conta. O nome precisa ser exatamente CONTA.ofx ou CONTA.xlsx, por exemplo AZEVEDO_ITAU.xlsx.")
        arquivos = st.file_uploader("Selecione os extratos", type=["ofx", "xlsx"], accept_multiple_files=True, key="upload_extratos")
        aprovados = []
        if arquivos:
            for arquivo in arquivos:
                try:
                    conta, extensao = validar_upload_extrato(arquivo.name, arquivo.size)
                    aprovados.append({"Arquivo": arquivo.name, "Conta": conta, "Formato": extensao, "Tamanho": f"{arquivo.size / 1024:.1f} KB", "_arquivo": arquivo})
                except ValueError as exc:
                    st.error(f"{arquivo.name}: {exc}")
            if aprovados:
                st.dataframe(pd.DataFrame([{k: v for k, v in item.items() if k != "_arquivo"} for item in aprovados]), use_container_width=True, hide_index=True)
                confirmar = st.checkbox("Confirmo que os arquivos são extratos oficiais exportados do banco.", key="confirmar_extratos")
                if st.button("Enviar extratos para processamento", type="primary", disabled=not confirmar, key="btn_importar_extratos"):
                    try:
                        drive, folder_id = _drive()
                        resultados = []
                        for item in aprovados:
                            arquivo = item["_arquivo"]
                            mime = mimetypes.guess_type(arquivo.name)[0] or "application/octet-stream"
                            salvo = drive_uploads.upload_bytes(drive, arquivo.name, arquivo.getvalue(), mime, folder_id)
                            resultados.append(salvo.get("name", arquivo.name))
                        st.success(f"{len(resultados)} extrato(s) salvo(s) no armazenamento persistente. O próximo Cenário 1 fará a sincronização.")
                        st.write("Arquivos enviados:", ", ".join(resultados))
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Não foi possível persistir os extratos: {type(exc).__name__}")


def pagina_agendamentos(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Agendamentos")
    st.markdown('<div class="eyebrow">Planejamento financeiro</div><div class="page-subtitle">Registre receitas e despesas futuras. Elas entram no fluxo projetado, mas não alteram o realizado.</div>', unsafe_allow_html=True)

    with st.form("novo_agendamento", clear_on_submit=True):
        st.markdown("#### Novo lançamento futuro")
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo = st.selectbox("Tipo", ["DESPESA", "RECEITA"])
            empresa_nova = st.selectbox("Empresa", EMPRESAS)
            descricao = st.text_input("Descrição", placeholder="Ex.: aluguel, patrocínio ou fornecedor")
            categoria = st.text_input("Categoria", placeholder="Ex.: aluguel, marketing, evento")
        with c2:
            favorecido = st.text_input("Favorecido / origem", placeholder="Nome do fornecedor ou cliente")
            valor = st.number_input("Valor", min_value=0.0, step=100.0, format="%.2f")
            data_prevista = st.date_input("Data prevista", value=date.today())
            recorrencia = st.selectbox("Recorrência", ["Única", "Mensal", "Semanal", "Anual"])
        with c3:
            venue_novo = st.text_input("Venue / unidade", placeholder="Opcional")
            status_novo = st.selectbox("Status", ["Agendado", "Pendente"])
            observacoes = st.text_area("Observações", placeholder="Condição, centro de custo ou referência")
        salvar = st.form_submit_button("Salvar agendamento", type="primary", use_container_width=True)

    if salvar:
        if not descricao.strip() or valor <= 0:
            st.error("Informe uma descrição e um valor maior que zero para salvar o agendamento.")
        else:
            identificador = f"AG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                gravar_agendamento({
                    "ID Agendamento": identificador,
                    "Tipo": tipo,
                    "Empresa": empresa_nova,
                    "Venue": venue_novo,
                    "Descrição": descricao.strip(),
                    "Categoria": categoria.strip() or "Outros",
                    "Favorecido": favorecido.strip(),
                    "Valor": round(valor, 2),
                    "Data Prevista": data_prevista.isoformat(),
                    "Recorrência": recorrencia,
                    "Status": status_novo,
                    "Data Baixa": "",
                    "ID Transação Banco": "",
                    "Observações": observacoes.strip(),
                })
                st.success(f"Agendamento {identificador} salvo. Ele já aparece no fluxo projetado.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001 — feedback seguro no painel
                st.error(f"Não foi possível salvar o agendamento: {type(exc).__name__}")

    agendamentos = dados_filtrados(frames, periodo, empresa, venue)["Agendamentos"].copy()
    if agendamentos.empty:
        empty_state("Nenhum agendamento cadastrado", "Use o formulário acima para começar a projetar entradas e saídas.")
        return
    st.markdown('<div class="section-heading"><h2>Agendamentos cadastrados</h2><span class="section-caption">Filtros aplicados ao período selecionado</span></div>', unsafe_allow_html=True)
    exibicao = agendamentos.copy()
    if "Valor" in exibicao.columns:
        exibicao["Valor"] = exibicao["Valor"].apply(moeda)
    st.dataframe(exibicao, use_container_width=True, hide_index=True)


def pagina_fluxo(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Fluxo de caixa")
    st.markdown('<div class="eyebrow">Planejamento financeiro</div><div class="page-subtitle">Consolidação do realizado com recebimentos e despesas agendadas.</div>', unsafe_allow_html=True)
    linhas = linhas_fluxo(frames, periodo, empresa, venue)
    resumo = totais(linhas)
    k = st.columns(4)
    with k[0]: metric_card("Entradas realizadas", moeda(resumo["entradas_realizadas"]), "Já recebidas")
    with k[1]: metric_card("Entradas previstas", moeda(resumo["entradas_previstas"]), "Parcelas em aberto")
    with k[2]: metric_card("Saídas previstas", moeda(resumo["saidas_previstas"]), "Despesas agendadas")
    with k[3]: metric_card("Saldo projetado", moeda(resumo["liquido_projetado"]), "Realizado + previsto")

    st.markdown('<div class="section-heading"><h2>Realizado x previsto</h2><span class="section-caption">O previsto não altera DRE, comissões ou baixas bancárias</span></div>', unsafe_allow_html=True)
    if not linhas:
        empty_state("Nenhum lançamento no período", "Cadastre contratos e despesas na aba Agendamentos para enxergar o fluxo futuro.")
        return

    fluxo = pd.DataFrame(linhas)
    fluxo["Valor_num"] = fluxo["Valor"].apply(numero)
    pivot = fluxo.pivot_table(index="Data", columns="Tipo", values="Valor_num", aggfunc="sum", fill_value=0).reset_index()
    tipos = ["ENTRADA_REALIZADA", "ENTRADA_PREVISTA", "SAIDA_REALIZADA", "SAIDA_PREVISTA"]
    for tipo in tipos:
        if tipo not in pivot.columns:
            pivot[tipo] = 0.0
    pivot["Fluxo líquido projetado"] = pivot["ENTRADA_REALIZADA"] + pivot["ENTRADA_PREVISTA"] - pivot["SAIDA_REALIZADA"] - pivot["SAIDA_PREVISTA"]

    fig = go.Figure()
    for tipo, nome, cor in (
        ("ENTRADA_REALIZADA", "Entrada realizada", COR_CASA),
        ("ENTRADA_PREVISTA", "Entrada prevista", "#75A9CC"),
        ("SAIDA_REALIZADA", "Saída realizada", COR_CASARAO),
        ("SAIDA_PREVISTA", "Saída prevista", "#E7B97B"),
    ):
        fig.add_trace(go.Bar(x=pivot["Data"], y=pivot[tipo], name=nome, marker_color=cor))
    fig.add_trace(go.Scatter(x=pivot["Data"], y=pivot["Fluxo líquido projetado"].cumsum(), name="Saldo acumulado", mode="lines+markers", line=dict(color=COR_VERDE, width=3), yaxis="y2"))
    fig.update_layout(barmode="relative", yaxis=dict(tickprefix="R$ ", separatethousands=True), yaxis2=dict(overlaying="y", side="right", tickprefix="R$ ", separatethousands=True, showgrid=False))
    st.plotly_chart(chart_layout(fig, 360), use_container_width=True, config={"displayModeBar": False})

    view = pivot[["Data", "ENTRADA_REALIZADA", "ENTRADA_PREVISTA", "SAIDA_REALIZADA", "SAIDA_PREVISTA", "Fluxo líquido projetado"]].rename(columns={
        "ENTRADA_REALIZADA": "Entradas realizadas", "ENTRADA_PREVISTA": "Entradas previstas",
        "SAIDA_REALIZADA": "Saídas realizadas", "SAIDA_PREVISTA": "Saídas previstas",
    })
    for coluna in view.columns[1:]:
        view[coluna] = view[coluna].apply(moeda)
    st.dataframe(view, use_container_width=True, hide_index=True)

    previstos = fluxo[fluxo["Tipo"].isin(("ENTRADA_PREVISTA", "SAIDA_PREVISTA"))].copy()
    if not previstos.empty:
        st.markdown('<div class="section-heading"><h2>Agendamentos no período</h2><span class="section-caption">Parcelas e despesas que ainda não foram realizadas</span></div>', unsafe_allow_html=True)
        colunas = [coluna for coluna in ["Data", "Tipo", "Empresa", "Descrição", "Categoria", "Valor", "Status", "Origem"] if coluna in previstos.columns]
        previstos["Valor"] = previstos["Valor"].apply(moeda)
        st.dataframe(previstos[colunas], use_container_width=True, hide_index=True)


def pagina_recebimentos(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Recebimentos")
    filtrados = dados_filtrados(frames, periodo, empresa, venue)
    receb, _ = recebimentos_despesas(filtrados)
    st.markdown('<div class="eyebrow">Operação financeira</div><div class="page-subtitle">Valores efetivamente recebidos e conciliados com parcelas.</div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1: metric_card("Total recebido", moeda(soma(receb, "Valor")), periodo)
    with k2: metric_card("Lançamentos", f"{len(receb):,}".replace(",", "."), "Recebimentos conciliados")
    with k3: metric_card("Empresas", str(receb["Empresa"].nunique()) if not receb.empty and "Empresa" in receb.columns else "0", "Com movimento")
    st.markdown('<div class="section-heading"><h2>Detalhamento</h2><span class="section-caption">Dados da planilha de recebimentos</span></div>', unsafe_allow_html=True)
    if receb.empty:
        empty_state("Nenhum recebimento no período", "Os recebimentos aparecerão aqui depois que o Cenário 1 baixar parcelas conciliadas.")
    else:
        st.dataframe(formatar_df(receb, ("Valor",)), use_container_width=True, hide_index=True)


def pagina_despesas(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Despesas")
    filtrados = dados_filtrados(frames, periodo, empresa, venue)
    _, despesas = recebimentos_despesas(filtrados)
    st.markdown('<div class="eyebrow">Operação financeira</div><div class="page-subtitle">Acompanhe custos por categoria, unidade e período.</div>', unsafe_allow_html=True)
    k1, k2 = st.columns(2)
    with k1: metric_card("Total de despesas", moeda(soma(despesas, "Valor")), periodo)
    with k2: metric_card("Lançamentos", f"{len(despesas):,}".replace(",", "."), "Despesas registradas")
    if despesas.empty:
        st.markdown('<div class="section-heading"><h2>Detalhamento</h2></div>', unsafe_allow_html=True)
        empty_state("Nenhuma despesa no período", "As despesas conciliadas pelos extratos aparecerão nesta página.")
        return
    left, right = st.columns([1, 1.2])
    with left:
        agrupada = despesas.copy()
        agrupada["Valor_num"] = agrupada["Valor"].apply(numero)
        categoria = agrupada.groupby("Categoria", dropna=False)["Valor_num"].sum().reset_index()
        fig = go.Figure(go.Bar(x=categoria["Categoria"], y=categoria["Valor_num"], marker_color=COR_CASARAO))
        fig.update_yaxes(tickprefix="R$ ", separatethousands=True)
        st.plotly_chart(chart_layout(fig, 310), use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown('<div class="section-heading"><h2>Detalhamento</h2></div>', unsafe_allow_html=True)
        st.dataframe(formatar_df(despesas, ("Valor",)), use_container_width=True, hide_index=True)


def pagina_contratos(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Contratos e parcelas")
    cr = dados_filtrados(frames, periodo, empresa, venue)["Contas a receber"]
    st.markdown('<div class="eyebrow">Base de contratos</div><div class="page-subtitle">Acompanhe o que está aberto, pago, vencido ou cancelado.</div>', unsafe_allow_html=True)
    status = cr["Status"].astype(str) if not cr.empty and "Status" in cr.columns else pd.Series(dtype=str)
    k = st.columns(4)
    with k[0]: metric_card("Parcelas", str(len(cr)), "No período")
    with k[1]: metric_card("Em aberto", str((status == "Aberto").sum()), moeda(soma(cr[status == "Aberto"], "Valor Parcela")))
    with k[2]: metric_card("Em atraso", str((status == "Atrasado").sum()), moeda(soma(cr[status == "Atrasado"], "Valor Parcela")))
    with k[3]: metric_card("Pagas", str((status == "Pago").sum()), moeda(soma(cr[status == "Pago"], "Valor Parcela")))
    st.markdown('<div class="section-heading"><h2>Carteira de parcelas</h2><span class="section-caption">A fonte de verdade do matching bancário</span></div>', unsafe_allow_html=True)
    if cr.empty:
        empty_state("Nenhum contrato cadastrado", "Cadastre contratos reais na aba Contas_a_Receber para ativar o acompanhamento financeiro.")
    else:
        st.dataframe(formatar_df(cr, ("Valor Total", "Valor Parcela")), use_container_width=True, hide_index=True)


def pagina_dre(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "DRE")
    dre = dados_filtrados(frames, periodo, empresa, venue)["DRE"]
    st.markdown('<div class="eyebrow">Resultado gerencial</div><div class="page-subtitle">Demonstrativo de resultado com impostos, custos, comissões e margem.</div>', unsafe_allow_html=True)
    if dre.empty:
        empty_state("Nenhuma DRE gerada para este período", "O Cenário 6 gera a DRE automaticamente às sextas-feiras.")
        return
    if "Empresa" in dre.columns:
        for coluna in ("Receita Bruta", "Impostos", "Custos Variáveis", "Comissões", "Custos Fixos", "Lucro Operacional"):
            if coluna in dre.columns:
                dre[coluna] = dre[coluna].apply(moeda)
    st.dataframe(dre, use_container_width=True, hide_index=True)


def pagina_comissoes(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Comissões")
    partes = [frames["Comissões Casa"], frames["Comissões Casarão"]]
    comissoes = pd.concat([filtrar_empresa(df, empresa) for df in partes if not df.empty], ignore_index=True) if any(not df.empty for df in partes) else pd.DataFrame()
    st.markdown('<div class="eyebrow">Remuneração comercial</div><div class="page-subtitle">Comissões calculadas sobre contratos assinados e estornos por cancelamento.</div>', unsafe_allow_html=True)
    k1, k2 = st.columns(2)
    with k1: metric_card("Comissões líquidas", moeda(soma(comissoes, "Líquido")), periodo)
    with k2: metric_card("Vendedores", str(comissoes["Vendedor"].nunique()) if not comissoes.empty and "Vendedor" in comissoes.columns else "0", "Com cálculo no período")
    if comissoes.empty:
        empty_state("Nenhuma comissão calculada", "O Cenário 3 registra as comissões da semana após os contratos assinados serem processados.")
    else:
        st.dataframe(formatar_df(comissoes, ("Base", "Comissão", "Estorno", "Líquido")), use_container_width=True, hide_index=True)


def pagina_operacao(frames: dict[str, pd.DataFrame], periodo: str, empresa: str, venue: str) -> None:
    render_header(periodo, empresa, "Operação")
    st.markdown('<div class="eyebrow">Saúde do sistema</div><div class="page-subtitle">Visão técnica para confirmar se os dados e as rotinas estão prontos.</div>', unsafe_allow_html=True)
    k = st.columns(3)
    with k[0]: metric_card("Abas monitoradas", str(len(ABAS)), "Google Sheets")
    with k[1]: metric_card("Abas com falha", str(len(FALHAS_LEITURA)), "Na última leitura")
    with k[2]: metric_card("Contas a receber", str(len(frames["Contas a receber"])), "Parcelas cadastradas")
    if FALHAS_LEITURA:
        st.markdown('<div class="section-heading"><h2>Falhas de leitura</h2></div>', unsafe_allow_html=True)
        for aba, erro in FALHAS_LEITURA.items():
            st.markdown(f'<div class="attention-card danger"><div class="attention-title">{aba}</div><div class="attention-text">Erro identificado: {erro}. Confira as credenciais, o compartilhamento e os cabeçalhos da aba.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-heading"><h2>Conectividade</h2></div>', unsafe_allow_html=True)
        st.markdown('<div class="empty-state"><div class="empty-title">Planilha conectada</div><div>As abas configuradas foram lidas sem erro nesta atualização.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading"><h2>Volume por aba</h2><span class="section-caption">Linhas lidas na última atualização</span></div>', unsafe_allow_html=True)
    volume = pd.DataFrame({"Aba": list(frames.keys()), "Linhas": [len(df) for df in frames.values()]})
    st.dataframe(volume, use_container_width=True, hide_index=True)


# Carrega os dados uma vez por sessão e usa o filtro apenas na apresentação.
frames = preparar_frames()
pagina, periodo, empresa, venue = render_sidebar(frames)

if pagina == "Resumo":
    pagina_resumo(frames, periodo, empresa, venue)
elif pagina == "Importações":
    pagina_importacoes(frames, periodo, empresa, venue)
elif pagina == "Agendamentos":
    pagina_agendamentos(frames, periodo, empresa, venue)
elif pagina == "Fluxo de caixa":
    pagina_fluxo(frames, periodo, empresa, venue)
elif pagina == "Recebimentos":
    pagina_recebimentos(frames, periodo, empresa, venue)
elif pagina == "Despesas":
    pagina_despesas(frames, periodo, empresa, venue)
elif pagina == "Contratos":
    pagina_contratos(frames, periodo, empresa, venue)
elif pagina == "DRE":
    pagina_dre(frames, periodo, empresa, venue)
elif pagina == "Comissões":
    pagina_comissoes(frames, periodo, empresa, venue)
elif pagina == "Operação":
    pagina_operacao(frames, periodo, empresa, venue)
""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
from datetime import date

# ─── CONFIGURAÇÃO DA PÁGINA ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Horas Extras - Manutenção",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 Painel de Horas Extras — Manutenção")
st.markdown("---")

# ─── CAMINHOS DOS ARQUIVOS ────────────────────────────────────────────────────
CAMINHO_NORTE = (
    "https://usinaxavantes-my.sharepoint.com/:x:/g/personal/"
    "jefferson_ferreira_usinaxavantes_onmicrosoft_com/"
    "IQCJy61pO1IpQIfqerZclJO_AXYMNtQVZbVN6_gq9b36mIo?e=hQaxYV&download=1"
)

CAMINHO_XAVANTES = (
    "https://usinaxavantes-my.sharepoint.com/:x:/g/personal/"
    "jefferson_ferreira_usinaxavantes_onmicrosoft_com/"
    "IQCs9x2Y5tE5SpbSw-pHPgi-AfrHK6d0ZcvqWkbyWVa53Ds?e=dKq6dz&download=1"
)

@st.cache_data(ttl=600)
def carregar_dados():

    resp_norte = requests.get(CAMINHO_NORTE)
    df_norte = pd.read_excel(
        io.BytesIO(resp_norte.content),
        sheet_name="Base_Dados",
        header=1,
        usecols=["Colaborador", "Data Hora Extra", "Total Horas Extras"]
    )
    df_norte.columns = ["colaborador", "data", "horas"]

    resp_xav = requests.get(CAMINHO_XAVANTES)
    df_xav = pd.read_excel(
        io.BytesIO(resp_xav.content),
        sheet_name="Base",
        header=1,
        usecols=["Colaborador", "Data", "Horas"]
    )
    df_xav.columns = ["colaborador", "data", "horas"]

    return df_norte, df_xav

# ─── PROCESSAMENTO COM FILTRO DE DATA ─────────────────────────────────────────
def processar(df, data_inicio, data_fim):
    df = df.copy()
    df["colaborador"] = df["colaborador"].astype(str).str.strip()
    df["horas"]       = pd.to_numeric(df["horas"], errors="coerce").fillna(0)
    df["data"]        = pd.to_datetime(df["data"], errors="coerce")

    df = df[
        (df["data"] >= pd.to_datetime(data_inicio)) &
        (df["data"] <= pd.to_datetime(data_fim))
    ]

    df["he_feitas"]      = df["horas"].clip(lower=0)
    df["he_compensadas"] = df["horas"].clip(upper=0).abs()

    resumo = df.groupby("colaborador").agg(
        he_feitas=("he_feitas", "sum"),
        he_compensadas=("he_compensadas", "sum")
    ).reset_index()

    resumo["he_a_pagar"] = (resumo["he_feitas"] - resumo["he_compensadas"]).clip(lower=0)
    resumo = resumo[~resumo["colaborador"].isin(["nan", "None", "", "Colaborador"])]

    return resumo.sort_values("he_a_pagar", ascending=False).reset_index(drop=True)

# ─── FORMATAÇÃO DE HORAS ──────────────────────────────────────────────────────
def formatar_horas(h):
    h = max(float(h), 0)
    horas   = int(h)
    minutos = round((h - horas) * 60)
    if minutos == 60:
        horas  += 1
        minutos = 0
    return f"{horas}h {minutos:02d}m" if minutos else f"{horas}h"

# ─── CARDS ────────────────────────────────────────────────────────────────────
def cards_resumo(resumo, nome_equipe):
    st.markdown(f"##### 📋 {nome_equipe}")
    c1, c2, c3 = st.columns(3)
    c1.metric("⏱️ HE Feitas",      formatar_horas(resumo["he_feitas"].sum()))
    c2.metric("🔄 HE Compensadas", formatar_horas(resumo["he_compensadas"].sum()))
    c3.metric("💰 HE a Pagar",     formatar_horas(resumo["he_a_pagar"].sum()))

# ─── TABELA ───────────────────────────────────────────────────────────────────
def tabela_resumo(resumo):
    df_display = resumo.copy()
    df_display["he_feitas"]      = df_display["he_feitas"].apply(formatar_horas)
    df_display["he_compensadas"] = df_display["he_compensadas"].apply(formatar_horas)
    df_display["he_a_pagar"]     = df_display["he_a_pagar"].apply(formatar_horas)
    df_display.columns = ["Colaborador", "HE Feitas", "HE Compensadas", "HE a Pagar"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# ─── GRÁFICO ──────────────────────────────────────────────────────────────────
def grafico_linhas(resumo_norte=None, resumo_xavantes=None):
    fig = go.Figure()

    config = [
        (resumo_norte,    "Norte",       "#1f77b4", "#aec7e8", "#ff7f0e"),
        (resumo_xavantes, "Xavantes GO", "#2ca02c", "#98df8a", "#d62728"),
    ]

    for resumo, label, c_feitas, c_comp, c_pagar in config:
        if resumo is None or resumo.empty:
            continue

        fig.add_trace(go.Scatter(
            x=resumo["colaborador"],
            y=resumo["he_feitas"],
            mode="lines+markers+text",
            name=f"{label} — HE Feitas",
            text=resumo["he_feitas"].apply(formatar_horas),
            textposition="top center",
            textfont=dict(size=10, color="#222222"),
            line=dict(color=c_feitas, width=2),
            marker=dict(size=8)
        ))

        fig.add_trace(go.Scatter(
            x=resumo["colaborador"],
            y=resumo["he_compensadas"],
            mode="lines+markers+text",
            name=f"{label} — HE Compensadas",
            text=resumo["he_compensadas"].apply(formatar_horas),
            textposition="top center",
            textfont=dict(size=10, color="#222222"),
            line=dict(color=c_comp, width=2, dash="dash"),
            marker=dict(size=8)
        ))

        fig.add_trace(go.Scatter(
            x=resumo["colaborador"],
            y=resumo["he_a_pagar"],
            mode="lines+markers+text",
            name=f"{label} — HE a Pagar",
            text=resumo["he_a_pagar"].apply(formatar_horas),
            textposition="top center",
            textfont=dict(size=11, color="#222222", family="Arial Black"),
            line=dict(color=c_pagar, width=2),
            marker=dict(size=8)
        ))

    fig.update_layout(
        title="Horas Extras por Colaborador",
        xaxis=dict(
            title="Colaboradores",
            tickfont=dict(
                color="#111111",
                size=13,
                family="Arial Black, Arial, sans-serif"
            )
        ),
        yaxis_title="Horas (decimal)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#f9f9f9",
        height=520,
    )
    st.plotly_chart(fig, use_container_width=True)

# ─── SIDEBAR — FILTROS ────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Filtros")

# ── botão de atualizar ──
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=date(2026, 4, 16),  # era maio, agora outubro
    format="DD/MM/YYYY"
)

data_fim = st.sidebar.date_input(
    "Data Final",
    value=date(2026, 6, 15),  # era junho, agora novembro
    format="DD/MM/YYYY"
)

if data_inicio > data_fim:
    st.sidebar.error("⚠️ A data inicial não pode ser maior que a data final.")

equipe_selecionada = st.sidebar.multiselect(
    "Equipe",
    options=["Norte", "Xavantes GO"],
    default=["Norte", "Xavantes GO"]
)

# ─── EXECUÇÃO PRINCIPAL ───────────────────────────────────────────────────────
try:
    with st.spinner("Carregando dados..."):
        df_norte_raw, df_xav_raw = carregar_dados()

    resumo_norte = (
        processar(df_norte_raw, data_inicio, data_fim)
        if "Norte" in equipe_selecionada else None
    )

    resumo_xavantes = (
        processar(df_xav_raw, data_inicio, data_fim)
        if "Xavantes GO" in equipe_selecionada else None
    )

    st.subheader(
        f"📅 Período: {data_inicio.strftime('%d/%m/%Y')} "
        f"a {data_fim.strftime('%d/%m/%Y')}"
    )
    st.markdown("---")

    col_norte, col_xav = st.columns(2)

    with col_norte:
        if resumo_norte is not None and not resumo_norte.empty:
            cards_resumo(resumo_norte, "Equipe Norte")
            tabela_resumo(resumo_norte)
        elif "Norte" in equipe_selecionada:
            st.info("Nenhum registro encontrado para o período selecionado — Norte.")

    with col_xav:
        if resumo_xavantes is not None and not resumo_xavantes.empty:
            cards_resumo(resumo_xavantes, "Equipe Xavantes GO")
            tabela_resumo(resumo_xavantes)
        elif "Xavantes GO" in equipe_selecionada:
            st.info("Nenhum registro encontrado para o período selecionado — Xavantes GO.")

    st.markdown("---")

    if (resumo_norte is not None and not resumo_norte.empty) or \
       (resumo_xavantes is not None and not resumo_xavantes.empty):
        grafico_linhas(resumo_norte, resumo_xavantes)

except FileNotFoundError as e:
    st.error(f"❌ Arquivo não encontrado: {e}")
except Exception as e:
    st.error(f"❌ Erro inesperado: {e}")

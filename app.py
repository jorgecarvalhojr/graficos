
import pandas as pd
import streamlit as st
import plotly.express as px
import json
from datetime import datetime
from datetime import timedelta

st.set_page_config(layout="wide", page_title="Análise de BOs - PRODEC")

# --- Parâmetros globais ---
DATA_CORTE_FIXA = pd.to_datetime("2025-07-18")
CSV_URLS = [
    "https://prodec.defesacivil.rj.gov.br/prodec.csv",
    "http://prodec.sistematica.info/public/prodec.csv"
]

@st.cache_data
def carregar_dados_ate_corte():
    for url in CSV_URLS:
        try:
            df = pd.read_csv(url, encoding='latin1')
            break
        except:
            continue
    df['data_solicitacao'] = pd.to_datetime(df['data_solicitacao'], errors='coerce')
    df['ano'] = df['data_solicitacao'].dt.year
    df['ocorrencia'] = df['ocorrencia'].fillna('Não Informada')
    df['redec'] = df['redec'].fillna('Não Informada')
    return df[df['data_solicitacao'] <= DATA_CORTE_FIXA]

@st.cache_data(ttl=600)
def carregar_dados_atuais():
    for url in CSV_URLS:
        try:
            df = pd.read_csv(url, encoding='latin1')
            break
        except:
            continue
    df['data_solicitacao'] = pd.to_datetime(df['data_solicitacao'], errors='coerce')
    df['ano'] = df['data_solicitacao'].dt.year
    df['ocorrencia'] = df['ocorrencia'].fillna('Não Informada')
    df['redec'] = df['redec'].fillna('Não Informada')
    return df

# --- Dados históricos (fixos até 18/07/2025) ---
st.header("📊 Dados até 18/07/2025 (fixos)")
df_corte = carregar_dados_ate_corte()

# Filtros
col1, col2, col3 = st.columns(3)
anos = sorted(df_corte['ano'].dropna().unique())
ocorrencias = sorted(df_corte['ocorrencia'].unique())
redecs = sorted(df_corte['redec'].unique())

ano_sel = col1.selectbox("Ano", anos, key="ano1")
ocorr_sel = col2.selectbox("Ocorrência", ocorrencias, key="ocorr1")
redec_sel = col3.selectbox("REDEC", redecs, key="redec1")

filtro_corte = (df_corte['ano'] == ano_sel) & (df_corte['ocorrencia'] == ocorr_sel) & (df_corte['redec'] == redec_sel)
dados_corte = df_corte[filtro_corte].groupby('municipio').size().reset_index(name='frequencia')

fig1 = px.bar(dados_corte, x='municipio', y='frequencia', color='frequencia',
              color_continuous_scale='thermal', title="BOs até 18/07/2025")
fig1.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig1, use_container_width=True)

# --- Dados atuais (dinâmicos) ---
st.header("📈 Dados acumulados atualizados (autoatualiza)")
df_atual = carregar_dados_atuais()

col4, col5, col6 = st.columns(3)
anos2 = sorted(df_atual['ano'].dropna().unique())
ano_sel2 = col4.selectbox("Ano", anos2, key="ano2")
ocorr_sel2 = col5.selectbox("Ocorrência", sorted(df_atual['ocorrencia'].unique()), key="ocorr2")
redec_sel2 = col6.selectbox("REDEC", sorted(df_atual['redec'].unique()), key="redec2")

filtro_atual = (df_atual['ano'] == ano_sel2) & (df_atual['ocorrencia'] == ocorr_sel2) & (df_atual['redec'] == redec_sel2)
dados_atual = df_atual[filtro_atual].groupby('municipio').size().reset_index(name='frequencia')

fig2 = px.bar(dados_atual, x='municipio', y='frequencia', color='frequencia',
              color_continuous_scale='viridis', title="BOs Acumulados até Agora")
fig2.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig2, use_container_width=True)

# --- Mapa interativo ---
st.header("🗺️ Mapa por Município (escala de calor)")
with open("geojs-33-mun.json", "r", encoding="utf-8") as f:
    geojson_rj = json.load(f)

fig_mapa = px.choropleth_mapbox(
    dados_atual,
    geojson=geojson_rj,
    locations='municipio',
    featureidkey='properties.name',
    color='frequencia',
    mapbox_style='carto-positron',
    center={"lat": -22.9, "lon": -43.3},
    zoom=6.5,
    opacity=0.7,
    color_continuous_scale="Reds",
    title="Mapa de Frequência por Município"
)
fig_mapa.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
st.plotly_chart(fig_mapa, use_container_width=True)

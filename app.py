
import pandas as pd
import streamlit as st
import plotly.express as px
import json
import io
import requests

st.set_page_config(layout="wide", page_title="Análise de BOs - PRODEC")

DATA_CORTE_FIXA = pd.to_datetime("2025-07-18")
CSV_URLS = [
    "https://prodec.defesacivil.rj.gov.br/prodec.csv",
    "https://pronadec.sistematica.info/prodec.csv"
]

@st.cache_data(ttl=600)
def carregar_dados():
    dfs = []
    for url in CSV_URLS:
        try:
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv"}
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            df = pd.read_csv(io.StringIO(response.text), encoding='latin1')
            dfs.append(df)
        except Exception as e:
            st.warning(f"Falha ao ler {url}: {e}")
            continue
    if not dfs:
        st.error("⚠️ Nenhum dado pôde ser carregado de nenhuma URL.")
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    df['data_solicitacao'] = pd.to_datetime(df['data_solicitacao'], errors='coerce')
    df['ano'] = df['data_solicitacao'].dt.year
    df['ocorrencia'] = df['ocorrencia'].fillna('Não Informada')
    df['redec'] = df['redec'].fillna('Não Informada')
    return df

df = carregar_dados()
if df.empty:
    st.stop()

# Filtros globais
st.sidebar.header("Filtros")
anos = sorted(df['ano'].dropna().unique())
ocorrencias = sorted(df['ocorrencia'].unique())
redecs = sorted(df['redec'].unique())

ano_sel = st.sidebar.selectbox("Ano", ["Todos"] + list(anos))
ocorr_sel = st.sidebar.selectbox("Ocorrência", ["Todos"] + ocorrencias)
redec_sel = st.sidebar.selectbox("REDEC", ["Todos"] + redecs)

df_filtrado = df.copy()
if ano_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['ano'] == ano_sel]
if ocorr_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['ocorrencia'] == ocorr_sel]
if redec_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['redec'] == redec_sel]

# Gráfico 1 - até a data de corte
st.header("📊 BOs até 18/07/2025")
df_corte = df_filtrado[df_filtrado['data_solicitacao'] <= DATA_CORTE_FIXA]
dados_corte = df_corte.groupby('municipio').size().reset_index(name='frequencia')
fig1 = px.bar(dados_corte, x='municipio', y='frequencia', color='frequencia',
              color_continuous_scale='thermal', title="BOs até 18/07/2025")
fig1.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2 - atualizados
st.header("📈 BOs acumulados (tempo real)")
dados_atual = df_filtrado.groupby('municipio').size().reset_index(name='frequencia')
fig2 = px.bar(dados_atual, x='municipio', y='frequencia', color='frequencia',
              color_continuous_scale='viridis', title="BOs Acumulados Atualizados")
fig2.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig2, use_container_width=True)

# Mapa
st.header("🗺️ Mapa por Município (Escala de Calor)")
with open("geojson_rj_municipios_isolado.json", "r", encoding="utf-8") as f:
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


import pandas as pd
import streamlit as st
import plotly.express as px
import json
import io
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            response.encoding = "latin1"
            df = pd.read_csv(io.StringIO(response.text))
            dfs.append(df)
        except Exception as e:
            st.warning(f"⚠️ Falha ao acessar {url}: {e}")
    if not dfs:
        st.error("❌ Nenhum dado pôde ser carregado.")
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    df['data_solicitacao'] = pd.to_datetime(df['data_solicitacao'], errors='coerce')
    df['ano'] = df['data_solicitacao'].dt.year
    df['ocorrencia'] = df['ocorrencia'].fillna('Não Informada')
    df['redec'] = df['redec'].fillna('Não Informada')
    df['municipio'] = df['municipio'].str.upper().str.strip()
    return df

df = carregar_dados()
if df.empty:
    st.stop()

# Filtros no topo
st.markdown("### Filtros Globais")
col1, col2, col3 = st.columns(3)
anos = sorted(df['ano'].dropna().unique())
ocorrencias = sorted(df['ocorrencia'].unique())
redecs = sorted(df['redec'].unique())

with col1:
    ano_sel = st.selectbox("Ano", ["Todos"] + list(anos), index=0)
with col2:
    ocorr_sel = st.selectbox("Ocorrência", ["Todos"] + ocorrencias, index=0)
with col3:
    redec_sel = st.selectbox("REDEC", ["Todos"] + redecs, index=0)

df_filtrado = df.copy()
if ano_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['ano'] == ano_sel]
if ocorr_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['ocorrencia'] == ocorr_sel]
if redec_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['redec'] == redec_sel]

# Gráficos lado a lado
st.markdown("### Frequência de BOs por Município")

col1, col2 = st.columns(2)

df_corte = df_filtrado[df_filtrado['data_solicitacao'] <= DATA_CORTE_FIXA]
dados_corte = df_corte.groupby('municipio').size().reset_index(name='frequencia')
dados_atual = df_filtrado.groupby('municipio').size().reset_index(name='frequencia')

with col1:
    st.subheader("📊 Até 18/07/2025")
    fig1 = px.bar(dados_corte, x='municipio', y='frequencia', color='frequencia',
                  color_continuous_scale='thermal')
    fig1.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("📈 Atualizado")
    fig2 = px.bar(dados_atual, x='municipio', y='frequencia', color='frequencia',
                  color_continuous_scale='viridis')
    fig2.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig2, use_container_width=True)

# Mapa abaixo
st.markdown("### 🗺️ Mapa de Frequência por Município")

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
    zoom=6.3,
    opacity=0.7,
    color_continuous_scale="Reds"
)
fig_mapa.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
st.plotly_chart(fig_mapa, use_container_width=True)

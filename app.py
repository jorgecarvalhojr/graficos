import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO
import json
import os

st.set_page_config(layout="wide")
st.title("📊 Frequência de BO por Município (RJ)")

# ----------- Função para carregar dados das URLs -----------
@st.cache_data(ttl=600)
def carregar_dados():
    urls = [
        "https://prodec.defesacivil.rj.gov.br/prodec.csv",
        "https://pronadec.sistematica.info/prodec.csv"
    ]
    frames = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))
                frames.append(df)
            else:
                st.warning(f"⚠️ Erro {response.status_code} ao acessar {url}")
        except Exception as e:
            st.warning(f"❌ Falha ao carregar {url}: {e}")

    if frames:
        df = pd.concat(frames, ignore_index=True)
        df['data_solicitacao'] = pd.to_datetime(df['data_solicitacao'], errors='coerce')
        df['ano'] = df['data_solicitacao'].dt.year
        df['municipio'] = df['municipio'].str.upper().str.strip()
        df['ocorrencia'] = df['ocorrencia'].fillna('NÃO INFORMADA')
        df['redec'] = df['redec'].fillna('NÃO INFORMADA')
        return df
    return pd.DataFrame()

# ----------- Carregar GeoJSON local -----------
@st.cache_data
def carregar_geojson():
    path = os.path.join(os.path.dirname(__file__), "RJ_Municipios_2024.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ----------- Carregando dados -----------
df = carregar_dados()
geojson = carregar_geojson()

if df.empty:
    st.error("❌ Não foi possível carregar dados.")
    st.stop()

# ----------- Filtros -----------
anos = ['TODOS'] + sorted(df['ano'].dropna().unique().tolist())
ocorrencias = ['TODAS'] + sorted(df['ocorrencia'].unique())
redec_opts = ['TODAS'] + sorted(df['redec'].unique())

col1, col2, col3 = st.columns(3)
ano_sel = col1.selectbox("Filtrar por Ano", anos)
ocur_sel = col2.selectbox("Filtrar por Ocorrência", ocorrencias)
redec_sel = col3.selectbox("Filtrar por REDEC", redec_opts)

# ----------- Gráfico 1: Acumulado até 18/07/2025 (fixo) -----------
col_esq, col_dir = st.columns(2)

with col_esq:
    st.subheader("📌 Gráfico Acumulado até 18/07/2025")
    df_fixo = df[df['data_solicitacao'] <= pd.to_datetime("2025-07-18")].copy()
    if ano_sel != 'TODOS':
        df_fixo = df_fixo[df_fixo['ano'] == ano_sel]
    if ocur_sel != 'TODAS':
        df_fixo = df_fixo[df_fixo['ocorrencia'] == ocur_sel]
    if redec_sel != 'TODAS':
        df_fixo = df_fixo[df_fixo['redec'] == redec_sel]
    freq_fixo = df_fixo['municipio'].value_counts().reset_index()
    freq_fixo.columns = ['municipio', 'frequencia']
    fig1 = px.bar(freq_fixo, x='municipio', y='frequencia',
                  title="BOs acumulados até 18/07/2025",
                  hover_data=['municipio', 'frequencia'])
    st.plotly_chart(fig1, use_container_width=True)

# ----------- Gráfico 2: Todos os dados acumulados (com atualização automática) -----------
with col_dir:
    st.subheader("📡 Gráfico com Atualização Automática (a cada 10 min)")
    df_atual = df.copy()
    if ano_sel != 'TODOS':
        df_atual = df_atual[df_atual['ano'] == ano_sel]
    if ocur_sel != 'TODAS':
        df_atual = df_atual[df_atual['ocorrencia'] == ocur_sel]
    if redec_sel != 'TODAS':
        df_atual = df_atual[df_atual['redec'] == redec_sel]
    freq_atual = df_atual['municipio'].value_counts().reset_index()
    freq_atual.columns = ['municipio', 'frequencia']
    fig2 = px.bar(freq_atual, x='municipio', y='frequencia',
                  title="BOs acumulados (dados atualizados)",
                  hover_data=['municipio', 'frequencia'])
    st.plotly_chart(fig2, use_container_width=True)

# ----------- Mapa Interativo com hover corrigido -----------
st.subheader("🗺️ Mapa Interativo de Frequência por Município (RJ)")

for feature in geojson['features']:
    nome_mun = feature['properties'].get('NM_MUN', '').upper().strip()
    freq = freq_atual.set_index('municipio').get('frequencia').get(nome_mun, 0)
    feature['properties']['frequencia'] = freq

fig_map = px.choropleth_mapbox(
    freq_atual,
    geojson=geojson,
    locations='municipio',
    featureidkey="properties.NM_MUN",
    color='frequencia',
    color_continuous_scale="YlOrRd",
    mapbox_style="carto-positron",
    center={"lat": -22.9, "lon": -43.2},
    zoom=6,
    opacity=0.7,
    hover_name='municipio',
    hover_data={'frequencia': True}
)

fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig_map, use_container_width=True)

import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO
import json
import os

st.set_page_config(layout="wide")
st.title("📊 Frequência de BO por Município (RJ)")

# ----------- Função para carregar dados de arquivos locais atualizados a cada 10 min -----------
@st.cache_data(ttl=600)
def carregar_dados():
    arquivos = ["prodec1.csv", "prodec2.csv"]  # Baixados previamente por cronjob
    frames = []
    for arq in arquivos:
        path = os.path.join(os.path.dirname(__file__), arq)
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                frames.append(df)
            except Exception as e:
                st.warning(f"Erro ao ler {arq}: {e}")
        else:
            st.warning(f"Arquivo não encontrado: {arq}")

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

# ----------- Gráfico 1: Acumulado até 18/07/2024 -----------
with st.columns(2)[0]:
    st.subheader("📌 Gráfico Acumulado (até 18/07/2024)")
    df_ate_2024 = df[df['data_solicitacao'] <= pd.to_datetime("2024-07-18")].copy()
    if ano_sel != 'TODOS':
        df_ate_2024 = df_ate_2024[df_ate_2024['ano'] == ano_sel]
    if ocur_sel != 'TODAS':
        df_ate_2024 = df_ate_2024[df_ate_2024['ocorrencia'] == ocur_sel]
    if redec_sel != 'TODAS':
        df_ate_2024 = df_ate_2024[df_ate_2024['redec'] == redec_sel]
    freq_ate_2024 = df_ate_2024['municipio'].value_counts().reset_index()
    freq_ate_2024.columns = ['municipio', 'frequencia']
    fig1 = px.bar(freq_ate_2024, x='municipio', y='frequencia',
                  title="BOs até 18/07/2024",
                  hover_data=['municipio', 'frequencia'])
    fig1.update_traces(hovertemplate='Município: %{x}<br>Frequência: %{y}')
    st.plotly_chart(fig1, use_container_width=True)

# ----------- Gráfico 2: Acumulado com atualizações -----------
with st.columns(2)[1]:
    st.subheader("🛁 Gráfico Acumulado (com atualização)")
    df_acumulado = df.copy()
    if ano_sel != 'TODOS':
        df_acumulado = df_acumulado[df_acumulado['ano'] == ano_sel]
    if ocur_sel != 'TODAS':
        df_acumulado = df_acumulado[df_acumulado['ocorrencia'] == ocur_sel]
    if redec_sel != 'TODAS':
        df_acumulado = df_acumulado[df_acumulado['redec'] == redec_sel]
    freq_acumulado = df_acumulado['municipio'].value_counts().reset_index()
    freq_acumulado.columns = ['municipio', 'frequencia']
    fig2 = px.bar(freq_acumulado, x='municipio', y='frequencia',
                  title="BOs Acumulados (atualizado)",
                  hover_data=['municipio', 'frequencia'])
    fig2.update_traces(hovertemplate='Município: %{x}<br>Frequência: %{y}')
    st.plotly_chart(fig2, use_container_width=True)

# ----------- Mapa Interativo -----------
st.subheader("🗺️ Mapa Interativo de Frequência por Município (RJ)")
geo_ids = []
valores = []
for feature in geojson['features']:
    nome_mun = feature['properties'].get('NM_MUN', '').upper().strip()
    geo_ids.append(feature['properties']['CD_MUN'])
    freq = freq_acumulado.set_index('municipio').get('frequencia').get(nome_mun, 0)
    valores.append(freq)
    feature['properties']['frequencia'] = freq

fig_map = px.choropleth_mapbox(
    geojson=geojson,
    locations=geo_ids,
    featureidkey="properties.CD_MUN",
    color=valores,
    color_continuous_scale="YlOrRd",
    mapbox_style="carto-positron",
    center={"lat": -22.9, "lon": -43.2},
    zoom=6,
    opacity=0.7
)
fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig_map, use_container_width=True)

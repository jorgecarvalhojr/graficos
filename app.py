import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO
import json
import os

st.set_page_config(layout="wide")
st.title("📊 Frequência de BO por Município (RJ)")

# ----------- Função aprimorada para carregar dados das URLs -----------
@st.cache_data(ttl=600)
def carregar_dados():
    urls = [
        "https://prodec.defesacivil.rj.gov.br/prodec.csv",
        "https://pronadec.sistematica.info/prodec.csv"
    ]
    frames = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "text/csv,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=15, verify=False)
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
        df['redec'] = df['redec'].fillna('NÃO INFORMADA').str.upper().str.strip()

        # Forçar associação dos municípios à REDEC correta em caixa alta
        df.loc[df['municipio'].isin(['DUQUE DE CAXIAS', 'NOVA IGUAÇU']), 'redec'] = 'REDEC 02 - BAIXADA FLUMINENSE'

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

# ----------- Aplicando filtros -----------
df_filtrado = df.copy()
if ano_sel != 'TODOS':
    df_filtrado = df_filtrado[df_filtrado['ano'] == ano_sel]
if ocur_sel != 'TODAS':
    df_filtrado = df_filtrado[df_filtrado['ocorrencia'] == ocur_sel]
if redec_sel != 'TODAS':
    df_filtrado = df_filtrado[df_filtrado['redec'] == redec_sel]

st.info(f"Total de Municípios com Dados: {df_filtrado['municipio'].nunique()}")

# ----------- Gráfico 1: Acumulado até 18/07/2025 (fixo) -----------
col_esq, col_dir = st.columns(2)

with col_esq:
    st.subheader("📌 Gráfico Acumulado até 18/07/2025")
    df_fixo = df_filtrado[df_filtrado['data_solicitacao'] <= pd.to_datetime("2025-07-18")].copy()
    freq_fixo = df_fixo['municipio'].value_counts().reset_index()
    freq_fixo.columns = ['municipio', 'frequencia']
    total_fixo = freq_fixo['frequencia'].sum()
    st.markdown(f"**Total de BOs até 18/07/2025: {total_fixo}**")
    fig1 = px.bar(freq_fixo, x='municipio', y='frequencia',
                  title="BOs acumulados até 18/07/2025",
                  hover_data=['municipio', 'frequencia'])
    st.plotly_chart(fig1, use_container_width=True)

# ----------- Gráfico 2: Todos os dados acumulados (com atualização automática) -----------
with col_dir:
    st.subheader("📡 Gráfico com Atualização Automática (a cada 10 min)")
    freq_atual = df_filtrado['municipio'].value_counts().reset_index()
    freq_atual.columns = ['municipio', 'frequencia']
    total_atual = freq_atual['frequencia'].sum()
    st.markdown(f"**Total de BOs atualizados: {total_atual}**")
    fig2 = px.bar(freq_atual, x='municipio', y='frequencia',
                  title="BOs acumulados (dados atualizados)",
                  hover_data=['municipio', 'frequencia'])
    st.plotly_chart(fig2, use_container_width=True)

# ----------- Mapa Interativo ajustado para RJ com filtros -----------
st.subheader("🗺️ Mapa Interativo de Frequência por Município (RJ)")
# Mapeamento garantido: caixa alta, sem acento removido, igual ao GeoJSON
freq_atual['municipio_original'] = freq_atual['municipio'].str.upper().str.strip()

fig_map = px.choropleth_mapbox(
    freq_atual,
    geojson=geojson,
    locations='municipio_original',
    featureidkey="properties.NM_MUN",
    color='frequencia',
    color_continuous_scale="YlOrRd",
    mapbox_style="carto-positron",
    zoom=7,
    opacity=0.6,
    center={"lat": -22.9, "lon": -43.2},
    hover_name='municipio_original',
    hover_data=['frequencia']
)
fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig_map.update_traces(hovertemplate='<b>%{location}</b><br>Frequência: %{z}<extra></extra>')
st.plotly_chart(fig_map, use_container_width=True)
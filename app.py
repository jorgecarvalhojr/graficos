import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO
import json
import os
from datetime import datetime
import pytz
import time

from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide")

st_autorefresh(interval=600 * 1000, key="datarefresh")

# ----------- Função aprimorada para carregar dados das URLs -----------
@st.cache_data(ttl=600)
def carregar_dados(_timestamp):
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
        df.loc[df['municipio'].isin(['DUQUE DE CAXIAS', 'NOVA IGUAÇU']), 'redec'] = 'REDEC 02 - BAIXADA FLUMINENSE'
        return df
    return pd.DataFrame()

# ----------- Carregar GeoJSON local -----------
@st.cache_data
def carregar_geojson():
    path = os.path.join(os.path.dirname(__file__), "RJ_Municipios_2024.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ----------- Carregar dados com atualização a cada 10 minutos -----------
brasilia_tz = pytz.timezone('America/Sao_Paulo')
timestamp = datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M:%S")
st.title(f"📊 PRODEC - Registros por Município (RJ) - Última atualização: {timestamp}")
df = carregar_dados(timestamp)
geojson = carregar_geojson()
geo_municipios = {f['properties']['NM_MUN'].upper(): f['properties']['NM_MUN'] for f in geojson['features']}


if df.empty:
    st.error("❌ Não foi possível carregar dados.")
    st.stop()

# ----------- Filtros -----------
anos = ['TODOS'] + sorted(df['ano'].dropna().unique().tolist())
ocorrencias = ['TODAS'] + sorted(df['ocorrencia'].unique())
redec_opts = ['TODAS'] + sorted(df['redec'].unique())

col1, col2, col3 = st.columns(3)
ano_sel = col1.selectbox("Filtrar por Ano", anos)
ocur_sel = col2.multiselect("Filtrar por Ocorrência", ocorrencias, default=["TODAS"])
redec_sel = col3.selectbox("Filtrar por REDEC", redec_opts)

# ----------- Aplicando filtros -----------
df_filtrado = df.copy()
if ano_sel != 'TODOS':
    df_filtrado = df_filtrado[df_filtrado['ano'] == ano_sel]
if "TODAS" not in ocur_sel:
    df_filtrado = df_filtrado[df_filtrado['ocorrencia'].isin(ocur_sel)]
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
    st.markdown(f"**Total de Registros até 18/07/2025: {total_fixo}**")
    fig1 = px.bar(freq_fixo, x='municipio', y='frequencia',
                  title="Registros acumulados até 18/07/2025",
                  hover_data=['municipio', 'frequencia'])
    st.plotly_chart(fig1, use_container_width=True)

# ----------- Gráfico 2: Todos os dados acumulados (com atualização automática) -----------
with col_dir:
    st.subheader("📡 Gráfico com Atualização Automática")
    freq_atual = df_filtrado['municipio'].value_counts().reset_index()
    freq_atual.columns = ['municipio', 'frequencia']
    total_atual = freq_atual['frequencia'].sum()
    st.markdown(f"**Total de Registros atualizados: {total_atual}**")
    fig2 = px.bar(freq_atual, x='municipio', y='frequencia',
                  title="Registros acumulados (dados atualizados)",
                  hover_data=['municipio', 'frequencia'])
    st.plotly_chart(fig2, use_container_width=True)

# ----------- Mapa Interativo ajustado para RJ com filtros -----------
col_map1, col_map2 = st.columns(2)

# --- Mapa 1: Acumulado até 18/07/2025 (fixo) ---
with col_map1:
    st.subheader("🗺️ Mapa Acumulado até 18/07/2025")
    # Prepare para o mapa fixo
    freq_fixo['municipio_upper'] = freq_fixo['municipio'].str.upper().str.strip()
    freq_fixo['municipio_original'] = freq_fixo['municipio_upper'].map(geo_municipios)
    freq_fixo['municipio_original'] = freq_fixo['municipio_original'].fillna(freq_fixo['municipio'].replace({"PARATI": "Paraty"}))

    fig_map_fixo = px.choropleth_mapbox(
        freq_fixo,
        geojson=geojson,
        locations='municipio_original',
        featureidkey="properties.NM_MUN",
        color='frequencia',
        color_continuous_scale="YlOrRd",
        mapbox_style="white-bg",
        zoom=6.5,
        opacity=0.6,
        center={"lat": -22.3, "lon": -43},
        range_color=[0, max(freq_fixo['frequencia'].max(), 1)],
    )
    fig_map_fixo.update_layout(
        margin={"r": 20, "t": 40, "l": 20, "b": 0},
        showlegend=True,
        mapbox_layers=[
            {
                "sourcetype": "geojson",
                "source": geojson,
                "type": "fill",
                "color": "rgba(255,255,255,0)",
                "below": "traces"
            }
        ],
        height=450,
    )
    fig_map_fixo.update_traces(hovertemplate='<b>%{location}</b><br>Registros: %{z}<extra></extra>')
    st.plotly_chart(fig_map_fixo, use_container_width=True, key="map_fixo")

# --- Mapa 2: Dinâmico atualizado ---
with col_map2:
    st.subheader("🗺️ Mapa com Atualização Automática")
    freq_atual['municipio_upper'] = freq_atual['municipio'].str.upper().str.strip()
    freq_atual['municipio_original'] = freq_atual['municipio_upper'].map(geo_municipios)
    freq_atual['municipio_original'] = freq_atual['municipio_original'].fillna(freq_atual['municipio'].replace({"PARATI": "Paraty"}))

    fig_map_atual = px.choropleth_mapbox(
        freq_atual,
        geojson=geojson,
        locations='municipio_original',
        featureidkey="properties.NM_MUN",
        color='frequencia',
        color_continuous_scale="YlOrRd",
        mapbox_style="white-bg",
        zoom=6.5,
        opacity=0.6,
        center={"lat": -22.3, "lon": -43},
        range_color=[0, max(freq_atual['frequencia'].max(), 1)],
    )
    fig_map_atual.update_layout(
        margin={"r": 20, "t": 40, "l": 20, "b": 0},
        showlegend=True,
        mapbox_layers=[
            {
                "sourcetype": "geojson",
                "source": geojson,
                "type": "fill",
                "color": "rgba(255,255,255,0)",
                "below": "traces"
            }
        ],
        height=450,
    )
    fig_map_atual.update_traces(hovertemplate='<b>%{location}</b><br>Registros: %{z}<extra></extra>')
    st.plotly_chart(fig_map_atual, use_container_width=True, key="map_atual")

# ----------- Tabela Interativa de Frequência por Município -----------
st.subheader("📋 Tabela Interativa de Registros por Município")
freq_table = freq_atual[['municipio_original', 'frequencia']].rename(columns={'municipio_original': 'Município', 'frequencia': 'Registros'})
freq_table = freq_table.sort_values(by='Município').reset_index(drop=True)
freq_table['Ordem'] = freq_table.index + 1
freq_table = freq_table[['Ordem', 'Município', 'Registros']]

# Aplicar CSS para alinhar à esquerda e definir largura
st.markdown(
    """
    <style>
    .css-1aumxhk {
        width: 40% !important;
    }
    .css-1aumxhk table {
        text-align: left !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.dataframe(freq_table, use_container_width=False, width=400, hide_index=True)

# ----------- Exportar dados filtrados -----------
csv = freq_table.to_csv(index=False)
st.download_button(
    label="📥 Baixar dados filtrados (CSV)",
    data=csv,
    file_name="frequencia_municipios_rj.csv",
    mime="text/csv"
)
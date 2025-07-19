import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO
import json
import os
from unidecode import unidecode


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
# --- Carregue freq_atual e geojson como já faz normalmente acima ---

# 1. Pegue os nomes dos municípios do GeoJSON
geojson_nomes = [f['properties']['NM_MUN'] for f in geojson['features']]
geojson_nomes_upper = [n.upper().strip() for n in geojson_nomes]
geo_municipios_dict = dict(zip(geojson_nomes_upper, geojson_nomes))

# 2. Padronize os nomes no freq_atual
freq_atual['municipio_upper'] = freq_atual['municipio'].str.upper().str.strip()

# 3. Mapeie para os nomes exatos do GeoJSON
freq_atual['municipio_original'] = freq_atual['municipio_upper'].map(geo_municipios_dict)

# 4. Debug: veja se ficou algo sem mapear
# Exemplo de patch manual (adicione outros se precisar):
freq_atual.loc[freq_atual['municipio_upper'] == "PARATI", "municipio_original"] = "Paraty"
# Repita linhas acima para outros casos se aparecerem aqui!

# 5. Garante todos do RJ no mapa (até os que não têm BO)
df_todos = pd.DataFrame({'municipio_original': geojson_nomes})
df_plot = df_todos.merge(freq_atual[['municipio_original', 'frequencia']], on='municipio_original', how='left')
df_plot['frequencia'] = df_plot['frequencia'].fillna(0)

df_plot['frequencia'] = pd.to_numeric(df_plot['frequencia'], errors='coerce').fillna(0)

# 7. Plote o RJ isolado, sem mapa base e sem vizinhos
fig = px.choropleth(
    df_plot,
    geojson=geojson,
    locations='municipio_original',
    featureidkey="properties.NM_MUN",
    color='frequencia',
    color_continuous_scale="Reds",   # Mais contrastante
    range_color=(0, df_plot['frequencia'].max()),
    hover_name='municipio_original',
    hover_data=['frequencia'],
)
fig.update_geos(
    fitbounds="locations",
    visible=False  # Remove mapa base, fica só o shape do RJ
)
fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    width=800, height=700
)
fig.update_traces(
    marker_line_width=0.7, marker_line_color='black',
    hovertemplate='<b>%{location}</b><br>Frequência: %{z}<extra></extra>'
)
st.subheader("🗺️ Mapa Interativo de Frequência por Município (RJ)")
st.plotly_chart(fig, use_container_width=True)
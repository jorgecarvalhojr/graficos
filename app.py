
import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.express as px
import requests
from io import StringIO
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Análise de BOs por Município - RJ")

@st.cache_data(ttl=600)
def baixar_csvs():
    urls = [
        "https://prodec.defesacivil.rj.gov.br/prodec.csv",
        "https://pronadec.sistematica.info/prodec.csv"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    frames = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10, verify=False)
            if r.status_code == 200:
                df = pd.read_csv(StringIO(r.text), sep=",")
                frames.append(df)
            else:
                st.warning(f"⚠️ Erro {r.status_code} ao acessar {url}")
        except Exception as e:
            st.warning(f"❌ Falha ao carregar {url}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else None

@st.cache_data(ttl=3600)
def carregar_geojson_local():
    try:
        gdf = gpd.read_file("RJ_Municipios_2024.json")
        gdf["NM_MUN"] = gdf["NM_MUN"].str.upper()
        return gdf
    except Exception as e:
        st.error(f"Erro ao carregar o mapa GeoJSON: {e}")
        return None

df = baixar_csvs()
geojson_gdf = carregar_geojson_local()

if df is None or geojson_gdf is None:
    st.stop()

# Processamento
df["data_solicitacao"] = pd.to_datetime(df["data_solicitacao"], errors="coerce")
df["ano"] = df["data_solicitacao"].dt.year
df["municipio"] = df["municipio"].str.upper()
df["redec"] = df["redec"].fillna("NÃO INFORMADO")
df["ocorrencia"] = df["ocorrencia"].fillna("NÃO INFORMADA")

# Filtros globais
anos = ["TODOS"] + sorted(df["ano"].dropna().unique().astype(str).tolist())
ocorrencias = ["TODAS"] + sorted(df["ocorrencia"].dropna().unique().tolist())
redecs = ["TODAS"] + sorted(df["redec"].dropna().unique().tolist())

col1, col2, col3 = st.columns(3)
ano_sel = col1.selectbox("Filtrar por Ano", anos)
ocor_sel = col2.selectbox("Filtrar por Ocorrência", ocorrencias)
redec_sel = col3.selectbox("Filtrar por REDEC", redecs)

# Aplicar filtros
df_filtrado = df.copy()
if ano_sel != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["ano"] == int(ano_sel)]
if redec_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["redec"] == redec_sel]
if ocor_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["ocorrencia"] == ocur_sel]

# Gráfico por município
municipios_contagem = df_filtrado["municipio"].value_counts().reset_index()
municipios_contagem.columns = ["municipio", "quantidade"]

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 📌 Acumulado até Hoje")
    fig1 = px.bar(municipios_contagem, x="municipio", y="quantidade", title="Frequência de BO por Município")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.markdown("### 📡 Atualizações Recentes")
    ultimos = df_filtrado[df_filtrado["data_solicitacao"] > pd.Timestamp.now() - pd.Timedelta("7D")]
    ultimos_agg = ultimos["municipio"].value_counts().reset_index()
    ultimos_agg.columns = ["municipio", "quantidade"]
    fig2 = px.bar(ultimos_agg, x="municipio", y="quantidade", title="Frequência (últimos 7 dias)")
    st.plotly_chart(fig2, use_container_width=True)

# Mapa de calor
st.markdown("### 🗺️ Mapa por Frequência de BO")
df_map = df_filtrado["municipio"].value_counts().reset_index()
df_map.columns = ["NM_MUN", "quantidade"]
mapa_merge = geojson_gdf.merge(df_map, on="NM_MUN", how="left")
mapa_merge["quantidade"] = mapa_merge["quantidade"].fillna(0)

fig_map = px.choropleth_mapbox(
    mapa_merge,
    geojson=mapa_merge.geometry.__geo_interface__,
    locations=mapa_merge.index,
    color="quantidade",
    hover_name="NM_MUN",
    mapbox_style="carto-positron",
    zoom=6.2, center={"lat": -22.9, "lon": -43.2},
    opacity=0.6
)
fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig_map, use_container_width=True)

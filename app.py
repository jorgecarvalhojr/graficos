
import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
from datetime import datetime
from io import StringIO

st.set_page_config(layout="wide")
st.title("📊 Análise de Frequência de BOs por Município (RJ)")

URLS = [
    "https://prodec.defesacivil.rj.gov.br/prodec.csv",
    "https://pronadec.sistematica.info/prodec.csv"
]

@st.cache_data(ttl=600)
def carregar_dados():
    frames = []
    for url in URLS:
        try:
            r = requests.get(url, verify=False, timeout=10)
            if r.status_code == 200:
                df = pd.read_csv(StringIO(r.text), sep=",")
                frames.append(df)
            else:
                st.warning(f"⚠️ Erro {r.status_code} ao acessar {url}")
        except Exception as e:
            st.warning(f"❌ Falha ao carregar {url}: {e}")

    if not frames:
        st.error("❌ Nenhum dado foi carregado.")
        return pd.DataFrame()

    df_total = pd.concat(frames, ignore_index=True)
    df_total["data_solicitacao"] = pd.to_datetime(df_total["data_solicitacao"], errors="coerce")
    df_total["ano"] = df_total["data_solicitacao"].dt.year
    df_total["MUNICIPIO"] = df_total["municipio"].str.upper().str.strip()
    df_total["REDEC"] = df_total["redec"].str.upper().str.strip()
    df_total["OCORRENCIA"] = df_total["ocorrencia"].str.upper().str.strip()
    return df_total

df = carregar_dados()

if df.empty:
    st.stop()

# Filtros Globais
col1, col2, col3 = st.columns(3)
anos = sorted(df["ano"].dropna().unique())
ano_selecionado = col1.selectbox("Filtrar por Ano", ["TODOS"] + [str(ano) for ano in anos])
ocorrencias = sorted(df["OCORRENCIA"].dropna().unique())
ocorrencia_sel = col2.selectbox("Filtrar por Ocorrência", ["TODAS"] + list(ocorrencias))
redec_opts = sorted(df["REDEC"].dropna().unique())
redec_sel = col3.selectbox("Filtrar por REDEC", ["TODAS"] + list(redec_opts))

df_filtrado = df.copy()
if ano_selecionado != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["ano"] == int(ano_selecionado)]
if ocorrencia_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["OCORRENCIA"] == ocorrencia_sel]
if redec_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["REDEC"] == redec_sel]

# Gráfico 1: Dados acumulados até 18/07/2025
corte_data = pd.to_datetime("2025-07-18")
df_corte = df_filtrado[df_filtrado["data_solicitacao"] <= corte_data]
acumulado = df_corte["MUNICIPIO"].value_counts().reset_index()
acumulado.columns = ["MUNICIPIO", "FREQUENCIA"]

# Gráfico 2: Dados completos atualizados
atualizado = df_filtrado["MUNICIPIO"].value_counts().reset_index()
atualizado.columns = ["MUNICIPIO", "FREQUENCIA"]

# Exibir gráficos lado a lado
col1, col2 = st.columns(2)
with col1:
    st.subheader("📌 Acumulado até 18/07/2025")
    fig1 = px.bar(acumulado, x="MUNICIPIO", y="FREQUENCIA", title="Acumulado até 18/07/2025")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("📡 Atualizações Recentes (Live)")
    fig2 = px.bar(atualizado, x="MUNICIPIO", y="FREQUENCIA", title="Dados Atualizados")
    st.plotly_chart(fig2, use_container_width=True)

# Carregar GeoJSON
geojson_url = "https://rj-mapas.s3.amazonaws.com/geojson_rj_municipios_ok.json"
try:
    geojson_data = requests.get(geojson_url, timeout=10).json()
except Exception as e:
    st.error(f"Erro ao carregar GeoJSON: {e}")
    geojson_data = None

# Mapa
if geojson_data:
    st.subheader("🗺️ Mapa de Frequência de BOs por Município (RJ)")
    df_mapa = df_filtrado["MUNICIPIO"].value_counts().reset_index()
    df_mapa.columns = ["MUNICIPIO", "FREQUENCIA"]

    fig_mapa = px.choropleth_mapbox(
        df_mapa,
        geojson=geojson_data,
        locations="MUNICIPIO",
        featureidkey="properties.name",
        color="FREQUENCIA",
        color_continuous_scale="Reds",
        mapbox_style="carto-positron",
        zoom=6,
        center={"lat": -22.9, "lon": -43.3},
        opacity=0.7,
        title="Frequência de BOs por Município (RJ)"
    )

    st.plotly_chart(fig_mapa, use_container_width=True)

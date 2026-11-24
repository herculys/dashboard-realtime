import os
import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

st.set_page_config(page_title="Dashboard Superloja Realtime", layout="wide")

# Cache curto (60s) para evitar sobrecarga no Neon mantendo atualização rápida
@st.cache_data(ttl=60)
def carregar_dados():
    conn = psycopg2.connect(os.environ["NEON_DATABASE_URL"])
    query = """
        SELECT 
            id_pedido, data_pedido, data_envio, dias_para_envio,
            modo_envio, segmento, cidade, estado_provincia, regiao,
            categoria, sub_categoria, nome_produto,
            vendas, quantidade, desconto, lucro, margem_lucro, _updated_at
        FROM analytics.fct_pedidos
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

df = carregar_dados()

# Cabeçalho e timestamp da última carga do ELT
ultima_atualizacao = pd.to_datetime(df["_updated_at"]).max()
st.title("📊 Dashboard Executivo — Superloja (Realtime)")
st.caption(f"Última sincronização ELT no Neon: {ultima_atualizacao.strftime('%d/%m/%Y %H:%M:%S')} UTC")

# Botão manual para forçar limpeza do cache e puxar dados novos do Neon
if st.sidebar.button("🔄 Atualizar dados agora"):
    st.cache_data.clear()
    st.rerun()

# Filtros na barra lateral
regioes = st.sidebar.multiselect("Região", options=sorted(df["regiao"].dropna().unique()))
categorias = st.sidebar.multiselect("Categoria", options=sorted(df["categoria"].dropna().unique()))

df_filtrado = df.copy()
if regioes:
    df_filtrado = df_filtrado[df_filtrado["regiao"].isin(regioes)]
if categorias:
    df_filtrado = df_filtrado[df_filtrado["categoria"].isin(categorias)]

# KPIs principais
col1, col2, col3, col4 = st.columns(4)
col1.metric("Faturamento Total", f"R$ {df_filtrado['vendas'].sum():,.2f}")
col2.metric("Lucro Total", f"R$ {df_filtrado['lucro'].sum():,.2f}")
margem_geral = (df_filtrado["lucro"].sum() / df_filtrado["vendas"].sum() * 100) if df_filtrado["vendas"].sum() > 0 else 0
col3.metric("Margem de Lucro", f"{margem_geral:.2f}%")
col4.metric("Pedidos Únicos", f"{df_filtrado['id_pedido'].nunique():,}")

st.divider()

# Gráficos com Plotly
g1, g2 = st.columns(2)

with g1:
    vendas_cat = df_filtrado.groupby("sub_categoria", as_index=False)["vendas"].sum().sort_values("vendas")
    fig_bar = px.bar(vendas_cat, x="vendas", y="sub_categoria", orientation="h", title="Vendas por Subcategoria")
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    df_filtrado["mes"] = pd.to_datetime(df_filtrado["data_pedido"]).dt.to_period("M").astype(str)
    evolucao = df_filtrado.groupby("mes", as_index=False)[["vendas", "lucro"]].sum()
    fig_line = px.line(evolucao, x="mes", y=["vendas", "lucro"], title="Evolução Mensal: Vendas vs Lucro")
    st.plotly_chart(fig_line, use_container_width=True)
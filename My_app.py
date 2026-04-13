import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION & THEME ---
st.set_page_config(page_title="Smiths Manufacturing | Quality Insights", layout="wide")

# Custom CSS to give it a professional "Industrial" feel
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data
def get_integrated_data():
    # Connect to provided SQLite databases
    with sqlite3.connect("production_data.sqlite") as conn_p, \
         sqlite3.connect("warranty_data.sqlite") as conn_w:
        
        df_prod = pd.read_sql("SELECT * FROM production_data", conn_p)
        df_warr = pd.read_sql("SELECT * FROM warranty_data", conn_w)

    df_prod['production_datetime'] = pd.to_datetime(df_prod['production_datetime'])
    
    # Aggregate warranty claims by batch
    warr_counts = df_warr.groupby('production_batch_number').agg(
        total_claims=('qc_table_id', 'count'),
        primary_defect_type=('defect_category', lambda x: x.mode()[0])
    ).reset_index()

    # Aggregate production parameters by batch
    # We calculate the mean and the standard deviation (to check for stability)
    prod_agg = df_prod.groupby('production_batch_number').agg(
        avg_temp=('mould_temperature', 'mean'),
        temp_stability=('mould_temperature', 'std'),
        avg_rpm=('screw_feedrate_rpm', 'mean'),
        material_batch=('material_batch_number', 'first'),
        machine=('machine_id', 'first'),
        timestamp=('production_datetime', 'min')
    ).reset_index()

    return pd.merge(prod_agg, warr_counts, on='production_batch_number', how='left').fillna(0)

df = get_integrated_data()

# --- DASHBOARD UI ---
st.title("🏭 Production-Warranty Correlation Dashboard")
st.markdown("Analysing the relationship between machine conditions and quality outcomes.")

# Top Level KPIs
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Warranty Claims", int(df['total_claims'].sum()))
m2.metric("Avg Mould Temp", f"{df['avg_temp'].mean():.2f}°C")
m3.metric("High-Risk Material", df.groupby('material_batch')['total_claims'].sum().idxmax())
m4.metric("Batches Analysed", len(df))

st.divider()

# Analysis Row
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Root Cause Analysis: Temperature vs. Defects")
    # Using a scatter plot with a trendline to prove correlation
    fig = px.scatter(df, x="avg_temp", y="total_claims", 
                     color="material_batch", size="total_claims",
                     trendline="ols", 
                     labels={"avg_temp": "Average Mould Temp (°C)", "total_claims": "Warranty Claims"})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Defect Types")
    # Quick view of what is actually going wrong
    defect_dist = df.groupby('primary_defect_type')['total_claims'].sum().reset_index()
    fig_pie = px.pie(defect_dist, values='total_claims', names='primary_defect_type', hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# Time and Material Analysis
st.subheader("Quality Timeline")
fig_line = px.line(df.sort_values('timestamp'), x='timestamp', y='total_claims', markers=True,
                   title="Claims Volume by Production Date")
st.plotly_chart(fig_line, use_container_width=True)

# Data Explorer
with st.expander("Explore Full Integrated Dataset"):
    st.dataframe(df.sort_values(by='total_claims', ascending=False), use_container_width=True)


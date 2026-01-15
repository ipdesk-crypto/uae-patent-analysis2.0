import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac
from PIL import Image

# --- ARCHISTRATEGOS SECURITY ---
def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], "LeoGiannotti2026!"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):
        return True
    st.markdown("<h1 style='text-align: center; color: #FF6600;'>🏛️ ARCHISTRATEGOS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Access Key:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Invalid Key.")
    return False

if not check_password():
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis 2.0", layout="wide", page_icon="🏛️")

# Custom Styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #FF6600; }
    </style>
""", unsafe_allow_html=True)

# --- DATA PROCESSING ENGINE ---
@st.cache_data
def load_all_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df_raw = pd.read_csv(file_path)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Timeline Standardization
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw['Application Date'] = pd.to_datetime(df_raw['Application Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date', 'Application Date'])
    
    # Monthly stamps for math precision
    df_raw['Priority_Month'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Arrival_Month'] = df_raw['Application Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Year_Int'] = df_raw['Earliest Priority Date'].dt.year.astype(int)
    
    # Most Recent Date Logic
    most_recent = df_raw['Application Date'].max().strftime('%B %d, %Y')
    
    # EXPLODE Logic for IPC Counts
    df_raw['IPC_List'] = df_raw['Classification'].astype(str).str.split(',')
    df_exploded = df_raw.explode('IPC_List')
    df_exploded['IPC_Clean'] = df_exploded['IPC_List'].str.strip()
    
    # Clean non-data
    df_exploded = df_exploded[~df_exploded['IPC_Clean'].str.contains("no classification", case=False, na=False)]
    df_exploded = df_exploded[df_exploded['IPC_Clean'] != 'nan']
    df_exploded['IPC_Section'] = df_exploded['IPC_Clean'].str[:1].str.upper()
    
    return df_exploded, df_raw, most_recent

df_exploded, df_raw, most_recent_date = load_all_data()

# --- HEADER WITH MOST RECENT DATE ---
st.markdown(f"""
    <div style="background-color: #002147; padding: 15px; border-radius: 10px; margin-bottom: 25px; border-bottom: 4px solid #FF6600;">
        <h4 style="color: white; margin: 0; text-align: center;">🏛️ ARCHISTRATEGOS PATENT INTELLIGENCE</h4>
        <p style="color: #FF6600; margin: 0; text-align: center; font-weight: bold;">MOST RECENT RECORD: {most_recent_date.upper()}</p>
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    menu = st.radio("Analytics Modules", ["Classification Distribution", "Unified Growth & Workload"])

# --- SHARED UI HELPERS ---
def apply_clean_layout(fig, title_text):
    fig.update_layout(
        title=title_text,
        xaxis_title="Year",
        yaxis_title="Number of Applications",
        template='plotly_white',
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='whitesmoke')
    return fig

# --- MODULE 1: CLASSIFICATION DISTRIBUTION ---
if menu == "Classification Distribution":
    st.header("📊 Classification Strengths & Section Trends")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df_exploded[df_exploded['IPC_Section'].isin(valid_sections)]
    
    # 1. Total Volume Bar Chart
    dist_counts = sect_df.groupby('IPC_Section').size().reset_index(name='Apps')
    fig_bar = px.bar(dist_counts, x='IPC_Section', y='Apps', text='Apps', 
                     color_discrete_sequence=['#FF6600'], labels={'Apps': 'Number of Applications'})
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_xaxes(showgrid=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    # 2. Section Growth Over Time
    st.subheader("Section Growth (Annual Volume)")
    sect_growth = sect_df.groupby(['Year_Int', 'IPC_Section']).size().reset_index(name='Apps')
    fig_growth = px.line(sect_growth, x='Year_Int', y='Apps', color='IPC_Section', markers=True)
    fig_growth = apply_clean_layout(fig_growth, "Yearly IPC Section Activity")
    st.plotly_chart(fig_growth, use_container_width=True)

# --- MODULE 2: UNIFIED GROWTH & WORKLOAD ---
elif menu == "Unified Growth & Workload":
    st.header("📈 Integrated Growth & Workload Analysis")
    st.info("Analysis shows 12-Month Rolling Totals (TTM). Areas are shaded for volume visualization.")

    all_codes = sorted(df_exploded['IPC_Clean'].unique())
    target_ipc = st.selectbox("Select IPC Code to Analyze (Dynamic Filtering):", ["TOTAL (Global)"] + all_codes)

    # Filtering Logic
    if target_ipc == "TOTAL (Global)":
        analysis_df = df_exploded.copy()
        raw_analysis_df = df_raw.copy()
    else:
        analysis_df = df_exploded[df_exploded['IPC_Clean'] == target_ipc]
        # For Arrival/Priority Workload we need the unique application IDs from the filtered exploded set
        unique_ids = analysis_df['Application Number'].unique()
        raw_analysis_df = df_raw[df_raw['Application Number'].isin(unique_ids)]

    # Timeline Setup
    full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')
    benchmark_val = len(df_raw) * 0.002

    # 1. Calculate Arrival Workload TTM
    arr_ttm = raw_analysis_df.groupby('Arrival_Month').size().reset_index(name='N')
    arr_ttm = arr_ttm.set_index('Arrival_Month').reindex(full_range, fill_value=0).rolling(window=12).sum().reset_index()

    # 2. Calculate Priority Workload TTM
    pri_ttm = raw_analysis_df.groupby('Priority_Month').size().reset_index(name='N')
    pri_ttm = pri_ttm.set_index('Priority_Month').reindex(full_range, fill_value=0).rolling(window=12).sum().reset_index()

    # 3. Calculate Application Types TTM (Based on Priority)
    type_grouped = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N')
    type_pivot = type_grouped.pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
    type_ttm = type_pivot.reindex(full_range, fill_value=0).rolling(window=12).sum()

    # --- BUILD THE UNIFIED PLOT ---
    fig_unified = go.Figure()

    # Add Workload: Arrival (Shaded)
    fig_unified.add_trace(go.Scatter(
        x=arr_ttm['index'], y=arr_ttm['N'],
        mode='lines', name='Workload: Date of Arrival',
        fill='tozeroy', line=dict(color='#FF6600', width=3),
        fillcolor='rgba(255, 102, 0, 0.15)'
    ))

    # Add Workload: Priority (Shaded)
    fig_unified.add_trace(go.Scatter(
        x=pri_ttm['index'], y=pri_ttm['N'],
        mode='lines', name='Workload: Earliest Priority',
        fill='tozeroy', line=dict(color='#002147', width=3),
        fillcolor='rgba(0, 33, 71, 0.15)'
    ))

    # Add Application Types (Shaded)
    colors = px.colors.qualitative.Safe
    for i, col in enumerate(type_ttm.columns):
        fig_unified.add_trace(go.Scatter(
            x=type_ttm.index, y=type_ttm[col],
            mode='lines', name=f'App Type: {col}',
            fill='tozeroy', line=dict(width=1.5, color=colors[i % len(colors)]),
            fillcolor=f'rgba({",".join([str(int(x)) for x in px.colors.hex_to_rgb(colors[i % len(colors)])])}, 0.1)'
        ))

    # Add 0.2% Benchmark Line
    fig_unified.add_trace(go.Scatter(
        x=full_range, y=[benchmark_val]*len(full_range),
        mode='lines', name='0.2% Benchmark',
        line=dict(color='red', width=2, dash='dash')
    ))

    # Layout Styling
    fig_unified = apply_clean_layout(fig_unified, f"Unified Analytics: {target_ipc} (Rolling 12-Month Total)")
    fig_unified.update_yaxes(title="Number of Applications (Integer TTM)")
    
    st.plotly_chart(fig_unified, use_container_width=True)
    
    st.markdown(f"**KPI Ref:** 0.2% Benchmark is **{benchmark_val:.2f}** applications.")

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

# Custom UI Styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; }
    .header-banner { 
        background-color: #002147; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center; 
        border-bottom: 5px solid #FF6600; 
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATA PROCESSING ENGINE ---
@st.cache_data
def load_and_prepare_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df_raw = pd.read_csv(file_path)
    df_raw.columns = df_raw.columns.str.strip()
    
    # 1. Date Standardization
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw['Application Date'] = pd.to_datetime(df_raw['Application Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date', 'Application Date'])
    
    # Generate timestamps for Rolling Total calculations
    df_raw['Priority_Month'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Arrival_Month'] = df_raw['Application Date'].dt.to_period('M').dt.to_timestamp()
    
    # Get the "Most Recent Record"
    most_recent_dt = df_raw['Application Date'].max()
    most_recent_str = most_recent_dt.strftime('%B %d, %Y')
    
    # 2. Explode IPC Codes for granular analysis
    df_raw['IPC_List'] = df_raw['Classification'].astype(str).str.split(',')
    df_exploded = df_raw.explode('IPC_List')
    df_exploded['IPC_Clean'] = df_exploded['IPC_List'].str.strip()
    
    # Clean non-classification artifacts
    df_exploded = df_exploded[~df_exploded['IPC_Clean'].str.contains("no classification", case=False, na=False)]
    df_exploded = df_exploded[df_exploded['IPC_Clean'] != 'nan']
    df_exploded['IPC_Section'] = df_exploded['IPC_Clean'].str[:1].str.upper()
    
    return df_exploded, df_raw, most_recent_str

df_exploded, df_raw, most_recent_label = load_and_prepare_data()

# --- HEADER WITH DYNAMIC DATE ---
st.markdown(f"""
    <div class="header-banner">
        <h2 style="color: white; margin: 0; font-family: serif;">🏛️ ARCHISTRATEGOS PATENT INTELLIGENCE</h2>
        <h4 style="color: #FF6600; margin: 5px 0 0 0; letter-spacing: 1px;">
            LATEST RECORDED DATA: {most_recent_label.upper()}
        </h4>
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    menu = st.radio("Analytics Modules", ["Global Distribution & Trends", "Unified Growth Analytics"])

# --- MODULE 1: GLOBAL DISTRIBUTION & TRENDS ---
if menu == "Global Distribution & Trends":
    st.header("📊 Total Patent Distribution (IPC A-H)")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Total Volume by Section
        sect_counts = df_exploded.groupby('IPC_Section').size().reset_index(name='Apps')
        fig_bar = px.bar(sect_counts, x='IPC_Section', y='Apps', text='Apps', 
                         color_discrete_sequence=['#FF6600'], title="Volume by Section")
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(xaxis_showgrid=False, template='plotly_white')
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        # Yearly Growth by Section
        df_exploded['Year'] = df_exploded['Earliest Priority Date'].dt.year
        yearly_sect = df_exploded.groupby(['Year', 'IPC_Section']).size().reset_index(name='Apps')
        fig_line_sect = px.line(yearly_sect, x='Year', y='Apps', color='IPC_Section', 
                                title="Yearly Section Growth", markers=True)
        fig_line_sect.update_xaxes(range=[2000, 2025], showgrid=False)
        fig_line_sect.update_layout(template='plotly_white')
        st.plotly_chart(fig_line_sect, use_container_width=True)

# --- MODULE 2: UNIFIED GROWTH ANALYTICS (TTM) ---
elif menu == "Unified Growth Analytics":
    st.header("📈 Unified Growth & Workload Density")
    st.info("The graph shows 12-Month Rolling Totals (TTM) to ensure whole numbers and smooth trends. Shaded areas represent cumulative volume.")

    # IPC Filter
    all_codes = sorted(df_exploded['IPC_Clean'].unique())
    target_ipc = st.selectbox("Filter Entire Analysis by IPC Code:", ["TOTAL (Global)"] + all_codes)

    # 1. Dynamic Filtering Logic
    if target_ipc == "TOTAL (Global)":
        type_df = df_exploded.copy()
        work_df = df_raw.copy()
    else:
        type_df = df_exploded[df_exploded['IPC_Clean'] == target_ipc]
        u_ids = type_df['Application Number'].unique()
        work_df = df_raw[df_raw['Application Number'].isin(u_ids)]

    # 2. Timeline Setup (2000-2025)
    full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')
    benchmark_val = len(df_raw) * 0.002 # 0.2% Global Benchmark

    # 3. Trailing Twelve Months (TTM) Calculations
    def get_ttm_series(df_in, date_col):
        counts = df_in.groupby(date_col).size().reset_index(name='N')
        return counts.set_index(date_col).reindex(full_range, fill_value=0).rolling(window=12).sum().reset_index()

    arr_ttm = get_ttm_series(work_df, 'Arrival_Month')
    pri_ttm = get_ttm_series(work_df, 'Priority_Month')
    
    type_group = type_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N')
    type_pivot = type_group.pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
    type_ttm = type_pivot.reindex(full_range, fill_value=0).rolling(window=12).sum()

    # --- 4. BUILD THE PLOT ---
    fig = go.Figure()

    # Workload: Arrival Date (Shaded)
    fig.add_trace(go.Scatter(
        x=arr_ttm['index'], y=arr_ttm['N'],
        mode='lines', name='Workload: Arrival Date',
        fill='tozeroy', line=dict(color='#FF6600', width=3),
        fillcolor='rgba(255, 102, 0, 0.15)'
    ))

    # Workload: Priority Date (Shaded)
    fig.add_trace(go.Scatter(
        x=pri_ttm['index'], y=pri_ttm['N'],
        mode='lines', name='Workload: Earliest Priority',
        fill='tozeroy', line=dict(color='#002147', width=3),
        fillcolor='rgba(0, 33, 71, 0.15)'
    ))

    # Application Types (Shaded)
    palette = px.colors.qualitative.Bold
    for i, type_name in enumerate(type_ttm.columns):
        color = palette[i % len(palette)]
        # Robust conversion to RGBA for shading
        rgba_color = color.replace('rgb', 'rgba').replace(')', ', 0.1)') if 'rgb' in color else color
        
        fig.add_trace(go.Scatter(
            x=type_ttm.index, y=type_ttm[type_name],
            mode='lines', name=f'App Type: {type_name}',
            fill='tozeroy', line=dict(width=1.5),
            fillcolor=rgba_color
        ))

    # 0.2% Benchmark Line (Red Dash)
    fig.add_trace(go.Scatter(
        x=full_range, y=[benchmark_val]*len(full_range),
        mode='lines', name='0.2% Benchmark',
        line=dict(color='red', width=2, dash='dash')
    ))

    # Final Layout Tweaks
    fig.update_layout(
        title=f"Unified Area Analysis (TTM): {target_ipc}",
        xaxis_title="Year",
        yaxis_title="Number of Applications",
        template='plotly_white',
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Strictly remove vertical grid lines and lock timeline
    fig.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='whitesmoke')

    st.plotly_chart(fig, use_container_width=True)
    st.write(f"📈 **Indicator:** The 0.2% Benchmark is currently set at **{benchmark_val:.2f}** annual apps.")

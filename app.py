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

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; }
    .recent-date { background-color: #002147; padding: 10px; border-radius: 8px; text-align: center; border-bottom: 4px solid #FF6600; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

# --- DATA PROCESSING ---
@st.cache_data
def load_all_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df_raw = pd.read_csv(file_path)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Dates
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw['Application Date'] = pd.to_datetime(df_raw['Application Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date', 'Application Date'])
    
    # Accurate Monthly timestamps
    df_raw['Priority_Month'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Arrival_Month'] = df_raw['Application Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Year_Int'] = df_raw['Earliest Priority Date'].dt.year.astype(int)
    
    # Recent Date Label
    most_recent = df_raw['Application Date'].max().strftime('%B %d, %Y')
    
    # Explode IPCs
    df_raw['IPC_List'] = df_raw['Classification'].astype(str).str.split(',')
    df_exploded = df_raw.explode('IPC_List')
    df_exploded['IPC_Clean'] = df_exploded['IPC_List'].str.strip()
    df_exploded = df_exploded[~df_exploded['IPC_Clean'].str.contains("no classification", case=False, na=False)]
    df_exploded = df_exploded[df_exploded['IPC_Clean'] != 'nan']
    df_exploded['IPC_Section'] = df_exploded['IPC_Clean'].str[:1].str.upper()
    
    return df_exploded, df_raw, most_recent

df_exploded, df_raw, most_recent_label = load_all_data()

# --- TOP HEADER ---
st.markdown(f"""
    <div class="recent-date">
        <h3 style="color: white; margin: 0;">🏛️ ARCHISTRATEGOS PATENT INTELLIGENCE</h3>
        <p style="color: #FF6600; font-weight: bold; margin: 0;">MOST RECENT RECORD: {most_recent_label.upper()}</p>
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
    menu = st.radio("Navigation", ["Classification Distribution", "Unified Vertical Analysis"])

# --- MODULE 1: CLASSIFICATION ---
if menu == "Classification Distribution":
    st.header("📊 IPC Section Distribution")
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df_exploded[df_exploded['IPC_Section'].isin(valid_sections)]
    
    counts = sect_df.groupby('IPC_Section').size().reset_index(name='Apps')
    fig_bar = px.bar(counts, x='IPC_Section', y='Apps', text='Apps', color_discrete_sequence=['#FF6600'])
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(xaxis_showgrid=False, template='plotly_white')
    st.plotly_chart(fig_bar, use_container_width=True)

# --- MODULE 2: UNIFIED VERTICAL ANALYSIS ---
elif menu == "Unified Vertical Analysis":
    st.header("⚖️ Unified Growth & Workload (Vertical Timeline)")
    st.info("The Y-axis shows Years (2000-2025). The X-axis shows the Number of Applications (12-Month Rolling Total).")

    all_codes = sorted(df_exploded['IPC_Clean'].unique())
    target_ipc = st.selectbox("Filter Analysis by IPC Code:", ["TOTAL (All)"] + all_codes)

    # Filter
    if target_ipc == "TOTAL (All)":
        work_df = df_raw.copy()
        type_df = df_exploded.copy()
    else:
        type_df = df_exploded[df_exploded['IPC_Clean'] == target_ipc]
        u_ids = type_df['Application Number'].unique()
        work_df = df_raw[df_raw['Application Number'].isin(u_ids)]

    # Timeline Setup (2000-2025)
    full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')
    benchmark_val = len(df_raw) * 0.002

    # Calculations
    def get_ttm(df_in, date_col):
        counts = df_in.groupby(date_col).size().reset_index(name='N')
        return counts.set_index(date_col).reindex(full_range, fill_value=0).rolling(window=12).sum().reset_index()

    arr_ttm = get_ttm(work_df, 'Arrival_Month')
    pri_ttm = get_ttm(work_df, 'Priority_Month')
    
    type_grouped = type_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N')
    type_pivot = type_grouped.pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
    type_ttm = type_pivot.reindex(full_range, fill_value=0).rolling(window=12).sum()

    # --- PLOTTING ---
    fig = go.Figure()

    # Priority Workload (Shaded)
    fig.add_trace(go.Scatter(
        y=pri_ttm['index'], x=pri_ttm['N'],
        mode='lines', name='Priority Workload',
        fill='tozerox', line=dict(color='#002147', width=2),
        fillcolor='rgba(0, 33, 71, 0.2)'
    ))

    # Arrival Workload (Shaded)
    fig.add_trace(go.Scatter(
        y=arr_ttm['index'], x=arr_ttm['N'],
        mode='lines', name='Arrival Workload',
        fill='tozerox', line=dict(color='#FF6600', width=2),
        fillcolor='rgba(255, 102, 0, 0.2)'
    ))

    # App Types (Shaded)
    safe_colors = px.colors.qualitative.Safe
    for i, col in enumerate(type_ttm.columns):
        # Robust color handling for Plotly rgb strings
        base_color = safe_colors[i % len(safe_colors)]
        rgba_color = base_color.replace('rgb', 'rgba').replace(')', ', 0.15)')
        
        fig.add_trace(go.Scatter(
            y=type_ttm.index, x=type_ttm[col],
            mode='lines', name=f'App Type: {col}',
            fill='tozerox', line=dict(width=1),
            fillcolor=rgba_color
        ))

    # Benchmark Line
    fig.add_trace(go.Scatter(
        y=full_range, x=[benchmark_val]*len(full_range),
        mode='lines', name='0.2% Benchmark',
        line=dict(color='red', width=2, dash='dash')
    ))

    # Unified Layout
    fig.update_layout(
        title=f"Vertical Analysis (TTM): {target_ipc}",
        xaxis_title="Number of Applications",
        yaxis_title="Year",
        template='plotly_white',
        hovermode="y unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_yaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=True, gridcolor='whitesmoke')
    fig.update_xaxes(showgrid=False) # Remove vertical grid lines

    st.plotly_chart(fig, use_container_width=True)
    st.write(f"Global 0.2% Benchmark: **{benchmark_val:.2f}** apps.")

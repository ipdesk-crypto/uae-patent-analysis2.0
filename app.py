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
st.set_page_config(page_title="UAE Patent Intelligence", layout="wide", page_icon="🏛️")

# Custom UI Styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    .date-header {
        color: #FF6600;
        text-align: center;
        font-weight: bold;
        font-size: 2.2em;
        margin-bottom: 20px;
        font-family: 'Times New Roman', Times, serif;
    }
    h1, h2, h3 { color: #002147; }
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-bottom: 3px solid #002147;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATA PROCESSING ENGINE ---
@st.cache_data
def load_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    
    # Clean Dates
    df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df = df.dropna(subset=['Earliest Priority Date', 'Application Date'])
    
    # Monthly Buckets
    df['Priority_Month'] = df['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df['Arrival_Month'] = df['Application Date'].dt.to_period('M').dt.to_timestamp()
    
    # Metadata
    latest_date_str = df['Application Date'].max().strftime('%B %d, %Y')
    
    # IPC Explosion
    df['IPC_List'] = df['Classification'].astype(str).str.split(',')
    df_exp = df.explode('IPC_List')
    df_exp['IPC_Clean'] = df_exp['IPC_List'].str.strip()
    # Filter out invalid entries
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("no classification|nan|There are no classifications", case=False, na=False)]
    
    return df_exp, df, latest_date_str

df_exp, df_raw, latest_update_val = load_data()

# --- TOP DATE DISPLAY ---
st.markdown(f'<div class="date-header">{latest_update_val.upper()}</div>', unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION & IPC SEARCH ---
with st.sidebar:
    try:
        st.image("logo.jpeg", use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    
    st.markdown("---")
    st.subheader("🔍 IPC Navigation")
    
    # Prepare IPC List
    all_ipcs = ["GLOBAL TOTAL"] + sorted(df_exp['IPC_Clean'].unique())
    
    # Initialize index in session state if not present
    if "ipc_index" not in st.session_state:
        st.session_state.ipc_index = 0

    # Search Box (Selectbox)
    target_ipc = st.selectbox(
        "Search or Select IPC:", 
        options=all_ipcs, 
        index=st.session_state.ipc_index,
        key="ipc_selector"
    )
    
    # Update index based on manual selectbox choice
    st.session_state.ipc_index = all_ipcs.index(target_ipc)

    # One-by-one Navigation Buttons
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Previous"):
            st.session_state.ipc_index = (st.session_state.ipc_index - 1) % len(all_ipcs)
            st.rerun()
    with col_next:
        if st.button("Next →"):
            st.session_state.ipc_index = (st.session_state.ipc_index + 1) % len(all_ipcs)
            st.rerun()

    st.markdown("---")
    smooth_val = st.slider("Smoothing Window (Months):", 1, 24, 12)

# --- FILTERING ---
if target_ipc == "GLOBAL TOTAL":
    analysis_df = df_exp.copy()
    work_df = df_raw.copy()
else:
    analysis_df = df_exp[df_exp['IPC_Clean'] == target_ipc]
    u_ids = analysis_df['Application Number'].unique()
    work_df = df_raw[df_raw['Application Number'].isin(u_ids)]

# --- ANALYTICS CALCULATIONS ---
full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')

def get_ma_series(data, date_col, window):
    counts = data.groupby(date_col).size().reset_index(name='N')
    return counts.set_index(date_col).reindex(full_range, fill_value=0).rolling(window=window).mean().reset_index()

pri_ma = get_ma_series(work_df, 'Priority_Month', smooth_val)
arr_ma = get_ma_series(work_df, 'Arrival_Month', smooth_val)

# Application Types Breakdown
type_pivot = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N') \
             .pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=smooth_val).mean()

# Key Markers
inception_date = pri_ma[pri_ma['N'] > 0]['index'].min()
peak_val = pri_ma['N'].max()
peak_date = pri_ma[pri_ma['N'] == peak_val]['index'].iloc[0] if peak_val > 0 else None

# --- METRIC DISPLAY ---
st.subheader(f"Analysis for IPC: {target_ipc}")
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Inception Date", inception_date.strftime('%Y-%m') if pd.notnull(inception_date) else "N/A")
with m2:
    st.metric("Peak Moving Avg", f"{peak_val:.2f}" if pd.notnull(peak_val) else "0.00")
with m3:
    st.metric("Total Applications", len(work_df))

# --- PLOTLY MOVING AVERAGE CHART ---
fig = go.Figure()

# 1. Growth Trend (Priority - Navy)
fig.add_trace(go.Scatter(
    x=pri_ma['index'], y=pri_ma['N'], mode='lines', name='Priority Growth Trend',
    fill='tozeroy', line=dict(color='#002147', width=4), fillcolor='rgba(0, 33, 71, 0.2)'
))

# 2. Arrival Workload (Orange)
fig.add_trace(go.Scatter(
    x=arr_ma['index'], y=arr_ma['N'], mode='lines', name='Arrival Workload',
    fill='tozeroy', line=dict(color='#FF6600', width=2), fillcolor='rgba(255, 102, 0, 0.1)'
))

# 3. Application Type Detail
palette = px.colors.qualitative.Safe
for i, col in enumerate(type_ma.columns):
    c = palette[i % len(palette)]
    # Convert rgb string to rgba for shading
    rgba = c.replace('rgb', 'rgba').replace(')', ', 0.15)') if 'rgb' in c else c
    fig.add_trace(go.Scatter(
        x=type_ma.index, y=type_ma[col], mode='lines', name=f'Type: {col}',
        fill='tozeroy', line=dict(width=1.5), fillcolor=rgba
    ))

# Growth Inception Marker
if pd.notnull(inception_date):
    fig.add_vline(x=inception_date, line_width=2, line_dash="dash", line_color="green")
    fig.add_annotation(x=inception_date, y=peak_val, text="INCEPTION", showarrow=True, font=dict(color="green"))

# 0.2% Volume Threshold
benchmark = (len(df_raw) * 0.002) / 12
fig.add_hline(y=benchmark, line_dash="dot", line_color="red", annotation_text="0.2% Threshold")

# Layout refinements
fig.update_layout(
    title=f"Moving Average Growth (2000-2025): {target_ipc}",
    xaxis_title="Timeline",
    yaxis_title="Monthly Apps (Moving Avg)",
    hovermode="x unified",
    template='plotly_white',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
fig.update_yaxes(showgrid=True, gridcolor='whitesmoke')

st.plotly_chart(fig, use_container_width=True)

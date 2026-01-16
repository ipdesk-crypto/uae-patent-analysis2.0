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
    .latest-update-banner {
        background-color: #FF6600;
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        border-radius: 5px;
        margin-bottom: 20px;
        font-size: 1.2em;
    }
    h1, h2, h3 { color: #002147; }
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
    latest_date = df['Application Date'].max().strftime('%B %d, %Y')
    
    # IPC Explosion
    df['IPC_List'] = df['Classification'].astype(str).str.split(',')
    df_exp = df.explode('IPC_List')
    df_exp['IPC_Clean'] = df_exp['IPC_List'].str.strip()
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("no classification|nan", case=False, na=False)]
    
    return df_exp, df, latest_date

df_exp, df_raw, latest_update_str = load_data()

# --- 1. LATEST RECORDED DATE (TOP PRIORITY) ---
st.markdown(f'<div class="latest-update-banner">DATABASE UPDATED UNTIL: {latest_update_str.upper()}</div>', unsafe_allow_html=True)

st.title("🏛️ Archistrategos: Patent Growth Analytics")

# --- SIDEBAR ---
with st.sidebar:
    try:
        st.image("logo.jpeg", use_container_width=True)
    except:
        pass
    st.markdown("### 🛠️ Graph Controls")
    smooth_val = st.slider("Smoothing (Moving Average Window):", 1, 24, 12, help="Adjust to see long-term growth trends vs monthly noise.")
    st.markdown("---")
    all_ipcs = sorted(df_exp['IPC_Clean'].unique())
    target_ipc = st.selectbox("Target IPC Classification:", ["GLOBAL TOTAL"] + all_ipcs)

# --- FILTERING ---
if target_ipc == "GLOBAL TOTAL":
    analysis_df = df_exp.copy()
    work_df = df_raw.copy()
else:
    analysis_df = df_exp[df_exp['IPC_Clean'] == target_ipc]
    u_ids = analysis_df['Application Number'].unique()
    work_df = df_raw[df_raw['Application Number'].isin(u_ids)]

# --- MATH: MOVING AVERAGE ---
full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')

def get_ma(data, date_col, window):
    counts = data.groupby(date_col).size().reset_index(name='N')
    return counts.set_index(date_col).reindex(full_range, fill_value=0).rolling(window=window).mean().reset_index()

pri_ma = get_ma(work_df, 'Priority_Month', smooth_val)
arr_ma = get_ma(work_df, 'Arrival_Month', smooth_val)

# App Types Pivot
type_pivot = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N') \
             .pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=smooth_val).mean()

# Growth Statistics
inception_date = pri_ma[pri_ma['N'] > 0]['index'].min()
peak_row = pri_ma.loc[pri_ma['N'].idxmax()] if not pri_ma['N'].empty else None

# --- 2. KPI METRICS (VISIBLE) ---
st.subheader(f"Lifecycle Summary: {target_ipc}")
m1, m2, m3 = st.columns(3)
m1.metric("Inception Date", inception_date.strftime('%Y-%m') if pd.notnull(inception_date) else "N/A")
m2.metric("Peak Moving Avg", f"{peak_row['N']:.2f}" if peak_row is not None else "0.00")
m3.metric("Total Applications", len(work_df))

# --- 3. THE GRAPH ---
fig = go.Figure()

# Priority Trend (Main Growth)
fig.add_trace(go.Scatter(
    x=pri_ma['index'], y=pri_ma['N'], mode='lines', name='Growth Trend (Priority)',
    fill='tozeroy', line=dict(color='#002147', width=4), fillcolor='rgba(0, 33, 71, 0.2)'
))

# Arrival Workload
fig.add_trace(go.Scatter(
    x=arr_ma['index'], y=arr_ma['N'], mode='lines', name='Arrival Workload',
    fill='tozeroy', line=dict(color='#FF6600', width=2), fillcolor='rgba(255, 102, 0, 0.1)'
))

# Specific Application Types
palette = px.colors.qualitative.Safe
for i, col in enumerate(type_ma.columns):
    c = palette[i % len(palette)]
    rgba = c.replace('rgb', 'rgba').replace(')', ', 0.15)')
    fig.add_trace(go.Scatter(
        x=type_ma.index, y=type_ma[col], mode='lines', name=f'App Type: {col}',
        fill='tozeroy', line=dict(width=1.5), fillcolor=rgba
    ))

# Growth Inception Marker
if pd.notnull(inception_date):
    fig.add_vline(x=inception_date, line_width=2, line_dash="dash", line_color="green")
    fig.add_annotation(x=inception_date, y=pri_ma['N'].max(), text="GROWTH START", showarrow=True, font=dict(color="green"))

# Global Benchmark (0.2%)
benchmark = len(df_raw) * 0.002 / 12 # Monthly average benchmark
fig.add_hline(y=benchmark, line_dash="dot", line_color="red", annotation_text="0.2% Volume Threshold")

fig.update_layout(
    title=f"Moving Average Growth Analysis ({smooth_val} Months Window)",
    xaxis_title="Timeline (2000 - 2025)",
    yaxis_title="Moving Average (Monthly Apps)",
    hovermode="x unified",
    template='plotly_white',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
fig.update_yaxes(showgrid=True, gridcolor='whitesmoke')

st.plotly_chart(fig, use_container_width=True)

st.caption("The graph uses a Moving Average to show consistent growth. 'Growth Start' indicates the first sustained activity for this IPC.")

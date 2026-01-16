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
st.set_page_config(page_title="UAE Patent Intelligence 2.0", layout="wide", page_icon="🏛️")

# Custom UI Styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; font-family: 'Arial Black', sans-serif; }
    .header-banner { 
        background-color: #002147; padding: 20px; border-radius: 10px; text-align: center; 
        border-bottom: 5px solid #FF6600; margin-bottom: 25px;
    }
    .metric-card {
        background-color: #f0f2f6; border-radius: 10px; padding: 15px; border-left: 5px solid #002147;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATA PROCESSING ENGINE ---
@st.cache_data
def load_and_prepare_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df_raw = pd.read_csv(file_path)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Date Standardization
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw['Application Date'] = pd.to_datetime(df_raw['Application Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date', 'Application Date'])
    
    # Monthly Timestamps
    df_raw['Priority_Month'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Arrival_Month'] = df_raw['Application Date'].dt.to_period('M').dt.to_timestamp()
    
    # Metadata
    most_recent_str = df_raw['Application Date'].max().strftime('%B %d, %Y')
    
    # IPC Explode
    df_raw['IPC_List'] = df_raw['Classification'].astype(str).str.split(',')
    df_exploded = df_raw.explode('IPC_List')
    df_exploded['IPC_Clean'] = df_exploded['IPC_List'].str.strip()
    df_exploded = df_exploded[~df_exploded['IPC_Clean'].str.contains("no classification|nan", case=False, na=False)]
    df_exploded['IPC_Section'] = df_exploded['IPC_Clean'].str[:1].str.upper()
    
    return df_exploded, df_raw, most_recent_str

df_exploded, df_raw, most_recent_label = load_and_prepare_data()

# --- HEADER ---
st.markdown(f"""
    <div class="header-banner">
        <h2 style="color: white; margin: 0;">🏛️ ARCHISTRATEGOS PATENT INTELLIGENCE</h2>
        <h4 style="color: #FF6600; margin: 5px 0 0 0;">LATEST RECORDED DATA: {most_recent_label.upper()}</h4>
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    try:
        st.image("logo.jpeg", use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    
    st.markdown("### ⚙️ Analysis Controls")
    smoothing_window = st.slider("Moving Average Window (Months):", 1, 24, 12, help="Higher values show smoother trends.")
    
    st.markdown("---")
    menu = st.radio("Navigation", ["Overview Distribution", "Dynamic Growth Engine"])

# --- MODULE 1: OVERVIEW ---
if menu == "Overview Distribution":
    st.header("📊 Patent Landscape (2000-2025)")
    sect_counts = df_exploded.groupby('IPC_Section').size().reset_index(name='Apps')
    fig_bar = px.bar(sect_counts, x='IPC_Section', y='Apps', text='Apps', 
                     color_discrete_sequence=['#FF6600'], title="Volume by IPC Section")
    fig_bar.update_layout(xaxis_showgrid=False, template='plotly_white')
    st.plotly_chart(fig_bar, use_container_width=True)

# --- MODULE 2: DYNAMIC GROWTH ENGINE ---
elif menu == "Dynamic Growth Engine":
    st.header("📈 Moving Average & Growth Inception")
    
    all_codes = sorted(df_exploded['IPC_Clean'].unique())
    target_ipc = st.selectbox("Select Technology (IPC) to Analyze Lifecycle:", ["TOTAL (Global)"] + all_codes)

    # Filtering
    if target_ipc == "TOTAL (Global)":
        type_df = df_exploded.copy()
        work_df = df_raw.copy()
    else:
        type_df = df_exploded[df_exploded['IPC_Clean'] == target_ipc]
        u_ids = type_df['Application Number'].unique()
        work_df = df_raw[df_raw['Application Number'].isin(u_ids)]

    # Analysis Timeframe
    full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')
    benchmark_val = (len(df_raw) * 0.002) # Global Volume Benchmark

    # TTM / Moving Average Logic
    def get_moving_avg(df_in, date_col, window):
        c = df_in.groupby(date_col).size().reset_index(name='N')
        # We use .sum() to show 'Annualized Rate' (Standard for growth)
        return c.set_index(date_col).reindex(full_range, fill_value=0).rolling(window=window).sum().reset_index()

    arr_ma = get_moving_avg(work_df, 'Arrival_Month', smoothing_window)
    pri_ma = get_moving_avg(work_df, 'Priority_Month', smoothing_window)
    
    type_pivot = type_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N') \
                 .pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
    type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=smoothing_window).sum()

    # Growth Inception logic: Find first date where total > 0
    inception_date = pri_ma[pri_ma['N'] > 0]['index'].min()
    peak_val = pri_ma['N'].max()
    peak_date = pri_ma[pri_ma['N'] == peak_val]['index'].iloc[0] if peak_val > 0 else None

    # KPI Row
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><b>Inception Date</b><br><span style='font-size:24px; color:#FF6600;'>{inception_date.strftime('%Y-%m') if pd.notnull(inception_date) else 'N/A'}</span></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><b>Peak Volume</b><br><span style='font-size:24px; color:#002147;'>{int(peak_val)} Apps / Year</span></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><b>Total Lifecycle Apps</b><br><span style='font-size:24px; color:#002147;'>{len(work_df)}</span></div>", unsafe_allow_html=True)

    # --- MAIN CHART ---
    fig = go.Figure()

    # Workload: Priority (Primary Growth Indicator)
    fig.add_trace(go.Scatter(
        x=pri_ma['index'], y=pri_ma['N'], mode='lines', name='Growth Trend (Priority)',
        fill='tozeroy', line=dict(color='#002147', width=4), fillcolor='rgba(0, 33, 71, 0.2)'
    ))

    # Workload: Arrival (Shaded)
    fig.add_trace(go.Scatter(
        x=arr_ma['index'], y=arr_ma['N'], mode='lines', name='Arrival Workload',
        fill='tozeroy', line=dict(color='#FF6600', width=2), fillcolor='rgba(255, 102, 0, 0.1)'
    ))

    # Application Types (Shaded)
    palette = px.colors.qualitative.Prism
    for i, col in enumerate(type_ma.columns):
        color = palette[i % len(palette)]
        rgba = color.replace('rgb', 'rgba').replace(')', ', 0.1)') if 'rgb' in color else color
        fig.add_trace(go.Scatter(
            x=type_ma.index, y=type_ma[col], mode='lines', name=f'Type: {col}',
            fill='tozeroy', line=dict(width=1), fillcolor=rgba
        ))

    # GROWTH INCEPTION MARKER
    if pd.notnull(inception_date):
        fig.add_vline(x=inception_date, line_width=2, line_dash="dot", line_color="green")
        fig.add_annotation(x=inception_date, y=peak_val*0.9, text="GROWTH START", showarrow=True, arrowhead=1, font=dict(color="green"))

    # BENCHMARK
    fig.add_trace(go.Scatter(x=full_range, y=[benchmark_val]*len(full_range), mode='lines', 
                             name='0.2% Volume Threshold', line=dict(color='red', width=2, dash='dash')))

    fig.update_layout(
        title=f"Lifecycle Analysis: {target_ipc} ({smoothing_window}-Month Moving Average)",
        xaxis_title="Timeline", yaxis_title="Annualized Application Rate",
        hovermode="x unified", template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='whitesmoke')

    st.plotly_chart(fig, use_container_width=True)

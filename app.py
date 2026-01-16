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

# Custom UI Styling for MAXIMUM VISIBILITY
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    
    /* Top Date Styling */
    .top-date {
        color: #FF6600;
        text-align: center;
        font-weight: 800;
        font-size: 3em;
        margin-bottom: 5px;
        letter-spacing: 2px;
    }

    /* Metric Card Styling */
    .metric-card {
        background-color: #002147;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        border-bottom: 6px solid #FF6600;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .metric-label {
        color: #FF6600;
        font-size: 1.1em;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .metric-value {
        color: #ffffff;
        font-size: 2.5em;
        font-weight: 900;
        font-family: 'Courier New', Courier, monospace;
    }
    
    h2, h3 { color: #002147; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data
def load_all_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df = df.dropna(subset=['Earliest Priority Date', 'Application Date'])
    df['Priority_Month'] = df['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df['Arrival_Month'] = df['Application Date'].dt.to_period('M').dt.to_timestamp()
    latest_date = df['Application Date'].max().strftime('%B %d, %Y')
    
    # IPC Explosion
    df['IPC_List'] = df['Classification'].astype(str).str.split(',')
    df_exp = df.explode('IPC_List')
    df_exp['IPC_Clean'] = df_exp['IPC_List'].str.strip()
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("no classification|nan", case=False, na=False)]
    df_exp['IPC_Section'] = df_exp['IPC_Clean'].str[:1].str.upper()
    return df_exp, df, latest_date

df_exp, df_raw, latest_update_str = load_all_data()

# --- 1. TOP DATE (STRICTLY DATE ONLY) ---
st.markdown(f'<div class="top-date">{latest_update_str.upper()}</div>', unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    try:
        st.image("logo.jpeg", use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    
    st.markdown("---")
    menu = st.radio("Navigation", ["Global Distribution", "Dynamic Growth Analysis"])
    
    if menu == "Dynamic Growth Analysis":
        st.markdown("### 🔍 IPC Navigation")
        all_ipcs = ["GLOBAL TOTAL"] + sorted(df_exp['IPC_Clean'].unique())
        
        if "ipc_idx" not in st.session_state: 
            st.session_state.ipc_idx = 0
        
        target_ipc = st.selectbox("Search/Select IPC:", all_ipcs, index=st.session_state.ipc_idx)
        st.session_state.ipc_idx = all_ipcs.index(target_ipc)
        
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← PREVIOUS"): 
                st.session_state.ipc_idx = (st.session_state.ipc_idx - 1) % len(all_ipcs)
                st.rerun()
        with col_next:
            if st.button("NEXT →"): 
                st.session_state.ipc_idx = (st.session_state.ipc_idx + 1) % len(all_ipcs)
                st.rerun()
        
        smooth_val = st.slider("Smoothing Window (Months):", 1, 24, 12)

# --- MODULE 1: GLOBAL DISTRIBUTION ---
if menu == "Global Distribution":
    st.header("📊 Patent Landscape Distribution")
    c_a, c_b = st.columns(2)
    with c_a:
        sect_counts = df_exp.groupby('IPC_Section').size().reset_index(name='Apps')
        fig1 = px.bar(sect_counts, x='IPC_Section', y='Apps', text='Apps', color_discrete_sequence=['#FF6600'], title="Total Apps by Section")
        st.plotly_chart(fig1, use_container_width=True)
    with c_b:
        df_exp['Year'] = df_exp['Earliest Priority Date'].dt.year
        yearly_sect = df_exp.groupby(['Year', 'IPC_Section']).size().reset_index(name='Apps')
        fig2 = px.line(yearly_sect, x='Year', y='Apps', color='IPC_Section', title="Yearly Section Growth (A-H)")
        fig2.update_xaxes(range=[2000, 2025])
        st.plotly_chart(fig2, use_container_width=True)

# --- MODULE 2: DYNAMIC GROWTH ANALYSIS ---
elif menu == "Dynamic Growth Analysis":
    # Data Filtering
    if target_ipc == "GLOBAL TOTAL":
        analysis_df = df_exp.copy()
        work_df = df_raw.copy()
    else:
        analysis_df = df_exp[df_exp['IPC_Clean'] == target_ipc]
        u_ids = analysis_df['Application Number'].unique()
        work_df = df_raw[df_raw['Application Number'].isin(u_ids)]

    # Moving Average Logic
    full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')
    def get_ma(data, date_col, window):
        c = data.groupby(date_col).size().reset_index(name='N')
        return c.set_index(date_col).reindex(full_range, fill_value=0).rolling(window=window).mean().reset_index()

    pri_ma = get_ma(work_df, 'Priority_Month', smooth_val)
    arr_ma = get_ma(work_df, 'Arrival_Month', smooth_val)
    
    # Statistics
    inception_dt = pri_ma[pri_ma['N'] > 0]['index'].min()
    peak_val = pri_ma['N'].max()
    inception_str = inception_dt.strftime('%Y-%m') if pd.notnull(inception_dt) else "N/A"

    # --- HIGH VISIBILITY METRIC CARDS ---
    st.write("---")
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Inception Date</div>
            <div class="metric-value">{inception_str}</div>
        </div>""", unsafe_allow_html=True)
        
    with m_col2:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Peak Moving Avg</div>
            <div class="metric-value">{peak_val:.2f}</div>
        </div>""", unsafe_allow_html=True)
        
    with m_col3:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Total Applications</div>
            <div class="metric-value">{len(work_df)}</div>
        </div>""", unsafe_allow_html=True)
    st.write("---")

    # --- THE GRAPH ---
    fig = go.Figure()
    
    # Priority Trend
    fig.add_trace(go.Scatter(x=pri_ma['index'], y=pri_ma['N'], mode='lines', name='Growth (Priority)',
                             fill='tozeroy', line=dict(color='#002147', width=5), fillcolor='rgba(0, 33, 71, 0.25)'))
    
    # Arrival Trend
    fig.add_trace(go.Scatter(x=arr_ma['index'], y=arr_ma['N'], mode='lines', name='Arrival Workload',
                             fill='tozeroy', line=dict(color='#FF6600', width=2), fillcolor='rgba(255, 102, 0, 0.1)'))

    # Type Detail
    type_pivot = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N') \
                 .pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
    type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=smooth_val).mean()
    
    colors = px.colors.qualitative.Bold
    for i, col_name in enumerate(type_ma.columns):
        fig.add_trace(go.Scatter(x=type_ma.index, y=type_ma[col_name], mode='lines', name=f'Type: {col_name}',
                                 fill='tozeroy', line=dict(width=1.5), fillcolor=colors[i % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.1)')))

    # Benchmark Line
    benchmark_line = (len(df_raw) * 0.002) / 12
    fig.add_hline(y=benchmark_line, line_dash="dot", line_color="red", annotation_text="0.2% Threshold")

    fig.update_layout(title=f"Trend Analytics: {target_ipc}", height=600, template='plotly_white', hovermode="x unified",
                      xaxis_title="Timeline", yaxis_title="Applications (Moving Average)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
    
    st.plotly_chart(fig, use_container_width=True)

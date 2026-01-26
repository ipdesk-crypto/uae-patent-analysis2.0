import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import hmac

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
    st.markdown("<h1 style='text-align: center; color: #FF6600;'>🏛️ ARCHISTRATEGOS 9.0</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Access Key:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Invalid Key.")
    return False

if not check_password():
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Intelligence 9.0", layout="wide", page_icon="🏛️")

# --- STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #001f3f; color: white; }
    h1, h2, h3 { color: #001f3f; font-weight: 800; }
    .stMetric { border-radius: 10px; border-top: 5px solid #FF6600; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    
    .metric-card {
        background-color: #001f3f;
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
    </style>
""", unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data
def load_and_preprocess():
    file_path = "2026 - 01- 23_ Data Structure for Patent Search and Analysis Engine - Type 5.csv"
    df = pd.read_csv(file_path)
    df = df[df['Application Number'] != 'Raw'].copy()
    
    # Date Core
    df['AppDate'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['PriorityDate'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df = df.dropna(subset=['AppDate', 'PriorityDate'])
    
    df['Year'] = df['AppDate'].dt.year
    df['Month_Name'] = df['AppDate'].dt.month_name()
    df['Arrival_Month'] = df['AppDate'].dt.to_period('M').dt.to_timestamp()
    df['Priority_Month'] = df['PriorityDate'].dt.to_period('M').dt.to_timestamp()
    
    # Firm/Agent
    df['Firm'] = df['Data of Agent - Name in English'].fillna("DIRECT FILING").str.strip().str.upper()
    
    # IPC Explosion
    df['IPC_Raw'] = df['Classification'].astype(str).str.split(',')
    df_exp = df.explode('IPC_Raw')
    df_exp['IPC_Clean'] = df_exp['IPC_Raw'].str.strip().str.upper()
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("NO CLASSIFICATION|NAN|NONE", na=False)]
    df_exp['IPC_Section'] = df_exp['IPC_Clean'].str[:1]
    df_exp['IPC_Class3'] = df_exp['IPC_Clean'].str[:3] 
    
    return df, df_exp

df_main, df_exp = load_and_preprocess()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    all_types = sorted(df_main['Application Type (ID)'].unique())
    selected_types = st.multiselect("Select Application Types:", all_types, default=all_types)
    df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
    df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]
    st.success(f"Records Analyzed: {len(df_f)}")

# --- DASHBOARD TABS ---
tabs = st.tabs([
    "📈 App Type Growth", 
    "🏢 Firm Intelligence", 
    "🔬 Firm Tech-Strengths",
    "🎯 STRATEGIC MAP", 
    "📊 IPC Classification", 
    "📉 Dynamic Moving Averages", 
    "📅 Monthly Filing"
])

# 1. APP TYPE GROWTH
with tabs[0]:
    st.header("Application Type Time-Series")
    growth = df_f.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
    fig1 = px.line(growth, x='Year', y='Count', color='Application Type (ID)', markers=True, height=750)
    st.plotly_chart(fig1, use_container_width=True)
    st.subheader("Growth Summary Table")
    st.dataframe(growth.pivot(index='Year', columns='Application Type (ID)', values='Count').fillna(0), use_container_width=True)

# 2. FIRM INTELLIGENCE
with tabs[1]:
    st.header("🏢 Agent / Firm Intelligence")
    top_firms = df_f['Firm'].value_counts().nlargest(10).index.tolist()
    selected_firms = st.multiselect("Select Firms to Compare:", sorted(df_f['Firm'].unique()), default=top_firms[:5])
    if selected_firms:
        firm_growth = df_f[df_f['Firm'].isin(selected_firms)].groupby(['Year', 'Firm']).size().reset_index(name='Apps')
        fig2 = px.line(firm_growth, x='Year', y='Apps', color='Firm', markers=True, height=800)
        st.plotly_chart(fig2, use_container_width=True)
        st.subheader("Firm Market Leaderboard")
        st.dataframe(df_f.groupby('Firm').size().reset_index(name='Total Apps').sort_values('Total Apps', ascending=False), use_container_width=True, hide_index=True)

# 3. FIRM TECH-STRENGTHS
with tabs[2]:
    st.header("🔬 Technology Strengths by Firm")
    if selected_firms:
        firm_ipc = df_exp_f[df_exp_f['Firm'].isin(selected_firms)].groupby(['Firm', 'IPC_Class3']).size().reset_index(name='Count')
        fig_strength = px.bar(firm_ipc, x='Count', y='Firm', color='IPC_Class3', orientation='h', height=850)
        st.plotly_chart(fig_strength, use_container_width=True)
        st.subheader("Tech-Strength Summary Table")
        st.dataframe(firm_ipc.pivot(index='Firm', columns='IPC_Class3', values='Count').fillna(0), use_container_width=True)

# 4. STRATEGIC MAP
with tabs[3]:
    st.header("🎯 Strategic Innovation & Competitor Map")
    land_data = df_exp_f.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
    fig_land = px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', height=850, color_continuous_scale='Viridis')
    st.plotly_chart(fig_land, use_container_width=True)
    st.subheader("White-Space Summary Table")
    st.dataframe(land_data.sort_values(by='Application Number', ascending=False), use_container_width=True, hide_index=True)

# 5. IPC CLASSIFICATION
with tabs[4]:
    st.header("IPC Section Distribution (A-H)")
    ipc_counts = df_exp_f.groupby('IPC_Section').size().reset_index(name='Count').sort_values('IPC_Section')
    st.plotly_chart(px.bar(ipc_counts, x='IPC_Section', y='Count', color='IPC_Section', text='Count', height=800), use_container_width=True)
    st.subheader("IPC Distribution Table")
    st.dataframe(ipc_counts, use_container_width=True, hide_index=True)

# 6. DYNAMIC MOVING AVERAGES (INTEGRATED FROM SECOND CODE)
with tabs[5]:
    st.header("📉 Dynamic Growth Analysis")
    
    # Logic from your second code for IPC Selection
    all_ipcs_nav = ["ALL IPC"] + sorted(df_exp_f['IPC_Clean'].unique())
    target_ipc = st.selectbox("Search/Select IPC:", all_ipcs_nav)
    smooth_val = st.slider("Smoothing Window (Months):", 1, 24, 12)

    # Filtering
    if target_ipc == "ALL IPC":
        analysis_df = df_exp_f.copy()
        work_df = df_f.copy()
    else:
        analysis_df = df_exp_f[df_exp_f['IPC_Clean'] == target_ipc]
        u_ids = analysis_df['Application Number'].unique()
        work_df = df_f[df_f['Application Number'].isin(u_ids)]

    # Moving Average Logic
    full_range = pd.date_range(start='2000-01-01', end=df_f['AppDate'].max(), freq='MS')
    def get_ma(data, date_col, window):
        c = data.groupby(date_col).size().reset_index(name='N')
        return c.set_index(date_col).reindex(full_range, fill_value=0).rolling(window=window).mean().reset_index()

    pri_ma = get_ma(work_df, 'Priority_Month', smooth_val)
    arr_ma = get_ma(work_df, 'Arrival_Month', smooth_val)
    
    # Metric Cards
    inception_dt = pri_ma[pri_ma['N'] > 0]['index'].min()
    inception_str = inception_dt.strftime('%Y-%m') if pd.notnull(inception_dt) else "N/A"
    
    st.write("---")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Inception Date</div><div class="metric-value">{inception_str}</div></div>', unsafe_allow_html=True)
    with m_col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Peak Moving Avg</div><div class="metric-value">{pri_ma["N"].max():.2f}</div></div>', unsafe_allow_html=True)
    with m_col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Applications</div><div class="metric-value">{len(work_df)}</div></div>', unsafe_allow_html=True)
    st.write("---")

    # The Graph with all specific traces from the second code
    fig_ma = go.Figure()
    
    # Priority Trend (Growth)
    fig_ma.add_trace(go.Scatter(x=pri_ma['index'], y=pri_ma['N'], mode='lines', name='Growth (Priority)',
                                fill='tozeroy', line=dict(color='#002147', width=5), fillcolor='rgba(0, 33, 71, 0.25)'))
    
    # Arrival Trend (Workload)
    fig_ma.add_trace(go.Scatter(x=arr_ma['index'], y=arr_ma['N'], mode='lines', name='Arrival Workload',
                                fill='tozeroy', line=dict(color='#FF6600', width=2), fillcolor='rgba(255, 102, 0, 0.1)'))

    # Type Detail (Each type with its own color)
    type_pivot = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N') \
                 .pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
    type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=smooth_val).mean()
    
    colors = px.colors.qualitative.Bold
    for i, col_name in enumerate(type_ma.columns):
        fig_ma.add_trace(go.Scatter(x=type_ma.index, y=type_ma[col_name], mode='lines', name=f'Type: {col_name}',
                                    fill='tozeroy', line=dict(width=1.5), fillcolor=colors[i % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.1)')))

    # Benchmark Line (0.2% of Total Dataset)
    benchmark_line = (len(df_main) * 0.002) / 12
    fig_ma.add_hline(y=benchmark_line, line_dash="dot", line_color="red", annotation_text="0.2% Threshold")

    fig_ma.update_layout(title=f"Trend Analytics: {target_ipc}", height=650, template='plotly_white', hovermode="x unified",
                         xaxis_title="Timeline", yaxis_title="Moving Average",
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_ma, use_container_width=True)
    
    # Summary Table for Data Scannability
    st.subheader("Momentum Summary Table")
    st.dataframe(pri_ma.rename(columns={'index':'Date', 'N':'Growth_MA'}).tail(12), use_container_width=True, hide_index=True)

# 7. MONTHLY FILING
with tabs[6]:
    st.header("📅 Monthly Filing Analysis")
    available_years = sorted(df_f['Year'].unique(), reverse=True)
    selected_year = st.selectbox("Choose a Year to analyze:", available_years)
    year_data = df_f[df_f['Year'] == selected_year]
    month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    monthly_counts = year_data.groupby('Month_Name').size().reindex(month_order, fill_value=0).reset_index(name='Apps')
    st.plotly_chart(px.bar(monthly_counts, x='Month_Name', y='Apps', text='Apps', title=f"Monthly Patent Filings in {selected_year}", height=750, color_discrete_sequence=['#001f3f']), use_container_width=True)
    st.subheader(f"Data Audit: {selected_year}")
    st.dataframe(monthly_counts, use_container_width=True, hide_index=True)

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
    </style>
""", unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data
def load_and_refine_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df_raw = pd.read_csv(file_path)
    df_raw.columns = df_raw.columns.str.strip()
    
    # 1. Timeline Setup
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw['Application Date'] = pd.to_datetime(df_raw['Application Date'], errors='coerce')
    
    # Drop rows without critical dates
    df_raw = df_raw.dropna(subset=['Earliest Priority Date', 'Application Date'])
    
    # Standardize Monthly Timestamps
    df_raw['Priority_Month'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Arrival_Month'] = df_raw['Application Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Year_Int'] = df_raw['Earliest Priority Date'].dt.year.astype(int)
    
    # 2. Explode IPCs (Every code counted separately)
    df_raw['Classification_Split'] = df_raw['Classification'].astype(str).str.split(',')
    df = df_raw.explode('Classification_Split')
    df['Classification_Clean'] = df['Classification_Split'].str.strip()
    
    # Remove rows with no specific data
    df = df[~df['Classification_Clean'].str.contains("no classification", case=False, na=False)]
    df = df[df['Classification_Clean'] != 'nan']
    df['IPC_Section'] = df['Classification_Clean'].str[:1].str.upper()
    
    return df, df_raw

df_exploded, df_original = load_and_refine_data()

# --- SIDEBAR ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    menu = st.radio("Navigation", ["Classification & Growth", "Growth Analysis (MA Zoom)", "Workload Analysis"])

# --- MODULE 1: CLASSIFICATION & GROWTH ---
if menu == "Classification & Growth":
    st.header("📊 Individual IPC Distribution & Trends")
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df_exploded[df_exploded['IPC_Section'].isin(valid_sections)]
    
    counts = sect_df.groupby('IPC_Section').size().reset_index(name='Apps')
    fig_hist = px.bar(counts, x='IPC_Section', y='Apps', text='Apps', 
                      title="Total Counts by IPC Section",
                      color_discrete_sequence=['#FF6600'], 
                      labels={'Apps': 'Number of Applications'})
    fig_hist.update_traces(textposition='outside')
    fig_hist.update_xaxes(showgrid=False)
    st.plotly_chart(fig_hist, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (MA ZOOM) ---
elif menu == "Growth Analysis (MA Zoom)":
    st.header("📈 Growth Analysis: 12-Month Rolling Total")
    all_codes = sorted(df_exploded['Classification_Clean'].unique())
    target_ipc = st.selectbox("Select Individual IPC Code to Zoom:", ["Total (All Classifications)"] + all_codes)

    if target_ipc == "Total (All Classifications)":
        analysis_df = df_exploded.copy()
    else:
        analysis_df = df_exploded[df_exploded['Classification_Clean'] == target_ipc]

    grouped = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='Counts')
    pivot_df = grouped.pivot(index='Priority_Month', columns='Application Type (ID)', values='Counts').fillna(0)
    
    full_range = pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS')
    pivot_df = pivot_df.reindex(full_range, fill_value=0)
    
    ma_df = pivot_df.rolling(window=12).sum().reset_index().rename(columns={'index': 'Timeline'})
    melted = ma_df.melt(id_vars='Timeline', var_name='App Type', value_name='Total_Apps')

    fig_ma = px.line(melted, x='Timeline', y='Total_Apps', color='App Type',
                     title=f"12-Month Growth Volume: {target_ipc}",
                     labels={'Total_Apps': 'Number of Applications', 'Timeline': 'Year'},
                     template='plotly_white')
    fig_ma.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
    fig_ma.update_yaxes(title="Number of Applications (TTM)", showgrid=True, gridcolor='whitesmoke')
    st.plotly_chart(fig_ma, use_container_width=True)

# --- MODULE 3: WORKLOAD ANALYSIS ---
elif menu == "Workload Analysis":
    st.header("⚖️ Workload Analysis & Benchmarking")
    st.write("Comparing arrival dates (Date of Arrival) against priority dates (Earliest Priority) using a Rolling 12-Month Total.")

    # 1. Calculate Arrival Workload
    arrival_workload = df_original.groupby('Arrival_Month').size().reset_index(name='Count')
    arrival_workload = arrival_workload.set_index('Arrival_Month').reindex(
        pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS'), fill_value=0
    ).rolling(window=12).sum().reset_index()
    arrival_workload.columns = ['Date', 'Arrival Workload']

    # 2. Calculate Priority Workload
    priority_workload = df_original.groupby('Priority_Month').size().reset_index(name='Count')
    priority_workload = priority_workload.set_index('Priority_Month').reindex(
        pd.date_range(start='2000-01-01', end='2025-12-01', freq='MS'), fill_value=0
    ).rolling(window=12).sum().reset_index()
    priority_workload.columns = ['Date', 'Priority Workload']

    # 3. Benchmark (0.2% of Total Records)
    total_records = len(df_original)
    benchmark_val = total_records * 0.002
    
    # 4. Merging for Plotting
    workload_df = pd.merge(arrival_workload, priority_workload, on='Date')
    workload_df['Benchmark (0.2%)'] = benchmark_val

    # Plotting with Area Fills
    fig_workload = go.Figure()

    # Priority Workload (Shaded Area)
    fig_workload.add_trace(go.Scatter(
        x=workload_df['Date'], y=workload_df['Priority Workload'],
        mode='lines', name='Earliest Priority Workload',
        fill='tozeroy', line=dict(color='#002147', width=2),
        fillcolor='rgba(0, 33, 71, 0.2)'
    ))

    # Arrival Workload (Shaded Area)
    fig_workload.add_trace(go.Scatter(
        x=workload_df['Date'], y=workload_df['Arrival Workload'],
        mode='lines', name='Arrival Date Workload',
        fill='tozeroy', line=dict(color='#FF6600', width=2),
        fillcolor='rgba(255, 102, 0, 0.2)'
    ))

    # Benchmark Line
    fig_workload.add_trace(go.Scatter(
        x=workload_df['Date'], y=workload_df['Benchmark (0.2%)'],
        mode='lines', name='0.2% Benchmark',
        line=dict(color='red', width=2, dash='dash')
    ))

    fig_workload.update_layout(
        title="Comparative Workload Analysis (TTM)",
        xaxis_title="Year",
        yaxis_title="Number of Applications",
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    fig_workload.update_xaxes(range=['2000-01-01', '2025-12-01'], dtick="M12", tickformat="%Y", showgrid=False)
    fig_workload.update_yaxes(showgrid=True, gridcolor='whitesmoke')

    st.plotly_chart(fig_workload, use_container_width=True)
    st.info(f"The 0.2% Benchmark is set at **{benchmark_val:.2f}** applications per year.")
